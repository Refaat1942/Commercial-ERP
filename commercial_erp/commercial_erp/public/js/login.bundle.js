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
	}
	if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
	else init();
})();
