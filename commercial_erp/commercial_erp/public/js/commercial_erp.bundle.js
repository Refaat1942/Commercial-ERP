// Language switcher (Arabic <-> English) for the signed-in user; the page reloads in the new language.
(function () {
	function install() {
		if (!window.frappe || !frappe.boot || frappe.session.user === "Guest") return;
		if (document.getElementById("ce-lang-switch")) return;
		var host = document.querySelector(".dock-utilities") || document.querySelector(".navbar .navbar-right, .navbar .nav");
		if (!host) return;
		var current = (frappe.boot.lang || "ar").split("-")[0];
		var target = current === "ar" ? "en" : "ar";
		var btn = document.createElement("button");
		btn.id = "ce-lang-switch";
		btn.className = "dock-item";
		btn.type = "button";
		btn.title = target === "en" ? "English" : "العربية";
		btn.innerHTML = '<span class="dock-item-icon ce-lang-label">' + (target === "en" ? "EN" : "ع") + "</span>";
		btn.addEventListener("click", function () {
			frappe.call({
				method: "commercial_erp.api.set_language",
				args: { lang: target },
				callback: function () { window.location.reload(); },
			});
		});
		host.prepend(btn);
	}
	// Translate dock tooltips/labels that upstream leaves in English (Assets, Setup, ...).
	function translateDock() {
		if (!window.__) return;
		document.querySelectorAll(".dock-item-label, .es-tooltip").forEach(function (el) {
			var src = el.getAttribute("data-ce-src") || el.textContent.trim();
			if (!src) return;
			el.setAttribute("data-ce-src", src);
			var t = __(src);
			if (t && t !== el.textContent) el.textContent = t;
		});
	}
	new MutationObserver(translateDock).observe(document.documentElement, { childList: true, subtree: true });
	// Open the shop dashboard instead of the generic apps screen; the developer ("Framework") pages
	// are not for shop users and open the setup home instead.
	var FRAMEWORK_PAGES = ["build", "email", "automation", "integrations", "website", "printing", "tools", "system-health-report"];
	function goHome() {
		if (!window.frappe || !frappe.boot || !frappe.set_route) return false;
		var path = window.location.pathname.replace(/\/$/, "");
		if (frappe.session.user === "Guest") return true;
		if (path === "/desk") frappe.set_route("shop");
		else if (FRAMEWORK_PAGES.indexOf(path.replace(/^\/desk\//, "")) !== -1) frappe.set_route("setup/home");
		return true;
	}
	// No email server in a shop setup: never offer "Email" / "New Email" on documents.
	var emailDone = false;
	function noEmail() {
		if (emailDone) return true;
		if (!window.frappe || !frappe.model || !frappe.model.can_email) return false;
		emailDone = true;
		frappe.model.can_email = function () { return false; };
		if (frappe.router && frappe.router.on) {
			frappe.router.on("change", goHome);
			frappe.router.on("change", pruneMenus); // print preview and other pages
		}
		if (frappe.ui && frappe.ui.form && frappe.ui.form.on) {
			// "Reset Password" mails a link; the administrator sets the password directly instead
			frappe.ui.form.on("User", "refresh", function (frm) {
				setTimeout(function () {
					frm.remove_custom_button(__("Reset Password"), __("Password"));
					frm.remove_custom_button(__("Create User Email"));
				}, 200);
				// users log in with the user name; the email is optional
				if (frm.is_new()) frm.toggle_reqd("username", true);
			});
			frappe.ui.form.on("*", "refresh", pruneMenus);
		}
		return true;
	}
	// Form menu entries a shop never uses (developer tools and documents of modules that are off).
	var DROP_MENU = [
		"Jump to field", "Show Links", "Copy to Clipboard", "Remind Me", "Undo", "Redo", "Documentation",
		"Settings", "Payment Request", "Invoice Discounting", "Dunning", "Maintenance Schedule",
		"Maintenance Visit", "Project", "Subscription", "Installation Note", "Work Order", "Auto Repeat",
		"Send SMS", "Create User Email", "Email", "New Email", "Raw Printing Setting", "Select Network Printer", "Asset", "Quality Inspection", "Subcontracting Order",
	];
	function pruneMenus(frm) {
		var hide = function () {
			var labels = {};
			DROP_MENU.forEach(function (l) { labels[__(l)] = 1; labels[l] = 1; });
			$(".page-head .dropdown-menu .dropdown-item").each(function () {
				var el = this.querySelector(".menu-item-label") || this;
				var text = (el.textContent || "").trim();
				text = text.slice(text.lastIndexOf(">") + 1).trim(); // "Create > Dunning" on narrow screens
				if (labels[text]) $(this).closest("li").length ? $(this).closest("li").hide() : $(this).hide();
			});
			// the print preview's "Email" button / icon
			var mail = __("Email");
			$(".page-head button, .page-head .btn").each(function () {
				var label = decodeURIComponent($(this).attr("data-label") || "");
				if (label === mail || label === "Email" || this.title === mail) $(this).hide();
			});
		};
		setTimeout(hide, 300);
		setTimeout(hide, 1500);
	}
	var mailTries = 0;
	if (!noEmail()) {
		var mailTimer = setInterval(function () {
			if (noEmail() || ++mailTries > 40) clearInterval(mailTimer);
		}, 100);
	}
	var homeTries = 0;
	var homeTimer = setInterval(function () {
		if (goHome() || ++homeTries > 40) clearInterval(homeTimer);
	}, 250);
	var tries = 0;
	var timer = setInterval(function () {
		install();
		if (document.getElementById("ce-lang-switch") || ++tries > 40) clearInterval(timer);
	}, 500);
})();
