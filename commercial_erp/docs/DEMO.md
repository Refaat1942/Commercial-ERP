# Demo guide / دليل التجربة

Two ways to try the system with realistic numbers. **Fake data only - never on a site with real business data.**

## A. Seed your own (test) site
```bash
cd /home/fes/fes-bench     # as user fes
bench --site SITE execute commercial_erp.setup.demo.seed        # 20 items, 8 customers, 4 suppliers, ~45 days of sales/purchases/payments/expenses
bench --site SITE execute commercial_erp.setup.demo.create_users --kwargs '{"password": "CHOOSE-A-PASSWORD"}'
bench --site SITE execute commercial_erp.setup.demo.clear       # removes ALL demo data and demo users again
```
Everything seeded is tagged (`DEMO-` item codes, `[تجريبي]` names, `DEMO-SEED` in remarks). Prices/quantities are invented; **no tax is applied**.

## B. A separate demo site for customers (recommended)
A second site with its own database on port **15162**, so the real site is untouched:
```bash
sudo DEMO_SITE=demo.local bash /home/fes/commercial_erp_src/deploy/create_demo_site.sh
sudo cat /root/commercial-erp-demo-credentials.txt      # password + the 4 demo logins (root-only file)
```
The demo owner is **not** a System Manager, so a shared demo login cannot change system settings. Reset the demo data any time:
`bench --site demo.local execute commercial_erp.setup.demo.clear` then `...demo.seed`.

## Links to hand to a customer (replace `<ip>`; demo site port 15162)
| Role | Login | Start here |
|---|---|---|
| Owner | `demo-owner@demo.example.com` | `http://<ip>:15162/desk/shop` (dashboard) · `/desk/query-report/Profit and Loss Statement` |
| Cashier | `demo-cashier@demo.example.com` | `/desk/sales-invoice/new` · `/desk/shop` |
| Storekeeper | `demo-store@demo.example.com` | `/desk/query-report/Stock Balance` · `/desk/query-report/Stock Projected Qty` · `/desk/stock-entry/new` |
| Accountant | `demo-accountant@demo.example.com` | `/desk/query-report/Accounts Receivable` · `/desk/payment-entry/new` · `/desk/query-report/General Ledger` |

Login page: `http://<ip>:15162/login` (language button top corner; the in-app button switches Arabic/English).

## Suggested 5-minute walkthrough
1. **Dashboard** (المحل): sales today/month, receivables/payables, 30-day sales chart.
2. **Sell**: new sales invoice -> pick *عميل نقدي* -> scan/choose item -> save/submit -> payment entry.
3. **Stock**: Stock Balance, then Low Stock Items (several demo items are below their reorder level on purpose).
4. **Money**: Customer Balances (credit sales) and Supplier Balances; Profit and Loss.
5. **Switch language** with the button in the rail; numbers/dates/EGP stay correct.
