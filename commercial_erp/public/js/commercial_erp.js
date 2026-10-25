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
	// Open the shop dashboard instead of the generic apps screen.
	function goHome() {
		if (!window.frappe || !frappe.boot || !frappe.set_route) return false;
		if (/^\/desk\/?$/.test(window.location.pathname) && frappe.session.user !== "Guest") {
			frappe.set_route("shop");
		}
		return true;
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
