// Login page: language toggle (sets the preferred-language cookie and reloads).
(function () {
	function init() {
		if (!document.getElementById("page-login") || document.getElementById("ce-login-lang")) return;
		var cur = (document.documentElement.lang || "ar").split("-")[0];
		var target = cur === "ar" ? "en" : "ar";
		var box = document.createElement("div");
		box.id = "ce-login-lang";
		var a = document.createElement("a");
		a.href = "#";
		a.textContent = target === "en" ? "English" : "العربية";
		a.addEventListener("click", function (e) {
			e.preventDefault();
			document.cookie = "preferred_language=" + target + "; path=/; max-age=31536000; SameSite=Lax";
			window.location.reload();
		});
		box.appendChild(a);
		document.body.appendChild(box);
		// log in with a user name (no email in a shop setup); "Forgot password" would need email
		var label = document.querySelector('label[for="login_email"]');
		if (label) label.textContent = cur === "ar" ? "اسم المستخدم" : "User name";
		var input = document.getElementById("login_email");
		if (input) {
			input.setAttribute("placeholder", cur === "ar" ? "مثال: Ahmed" : "e.g. Ahmed");
			input.setAttribute("autocapitalize", "off");
			input.setAttribute("autocorrect", "off");
			input.setAttribute("spellcheck", "false");
		}
		var forgot = document.querySelector('a[href="#forgot"]');
		if (forgot) forgot.style.display = "none";
	}
	if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
	else init();
})();
