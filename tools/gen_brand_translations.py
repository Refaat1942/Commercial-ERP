"""Regenerate the white-label translation overrides (run with the bench's python):

    env/bin/python apps/commercial_erp/tools/gen_brand_translations.py

For every UI string in ERPNext/Frappe containing the upstream product name, writes the same string
with "FES ERP" instead, to translations/en.csv and (using the upstream Arabic translation) ar.csv.
Hand-written overrides live in translations/_manual_ar.csv and always win.
"""

import csv
import io
import os
import sys

from babel.messages.pofile import read_po

BRAND = "FES ERP"
UPSTREAM_NAMES = ("ERPNext", "Erpnext", "ERPnext")
BENCH_APPS = os.path.abspath(
	sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "..")
)
OUT = os.path.join(os.path.dirname(__file__), "..", "commercial_erp", "translations")


def swap(text):
	for name in UPSTREAM_NAMES:
		text = text.replace(name, BRAND)
	return text


def has_name(text):
	return any(n in text for n in UPSTREAM_NAMES)


def messages(path):
	if not os.path.exists(path):
		return []
	with open(path, "rb") as f:
		catalog = read_po(f)
	return [m for m in catalog if m.id]


def main():
	apps = os.path.join(BENCH_APPS)
	en_rows, ar_rows = {}, {}
	for app in ("frappe", "erpnext"):
		locale = os.path.join(apps, app, app, "locale")
		ar = {
			(m.id if isinstance(m.id, str) else m.id[0], m.context): m.string
			for m in messages(os.path.join(locale, "ar.po"))
		}
		for m in messages(os.path.join(locale, "main.pot")):
			msgid = m.id if isinstance(m.id, str) else m.id[0]
			if not has_name(msgid):
				continue
			ctx = m.context or ""
			en_rows[(msgid, ctx)] = swap(msgid)
			translated = ar.get((msgid, m.context))
			if isinstance(translated, (tuple, list)):
				translated = translated[0]
			ar_rows[(msgid, ctx)] = swap(translated) if translated else swap(msgid)
	manual_rows = []
	for name in ("_glossary_ar.csv", "_manual_ar.csv"):  # later files win
		path = os.path.join(OUT, name)
		if os.path.exists(path):
			with open(path, newline="", encoding="utf-8") as f:
				manual_rows += [r for r in csv.reader(f) if r]
	for name, rows in (("en", en_rows), ("ar", ar_rows)):
		buf = io.StringIO()
		w = csv.writer(buf, lineterminator="\n")
		for (src, ctx), tr in sorted(rows.items()):
			w.writerow([src.replace("\n", "\\n"), tr.replace("\n", "\\n"), ctx])
		if name == "ar":
			for r in manual_rows:
				w.writerow(r)
		with open(os.path.join(OUT, f"{name}.csv"), "w", encoding="utf-8", newline="") as f:
			f.write(buf.getvalue())
		print(name, len(rows))


if __name__ == "__main__":
	main()
