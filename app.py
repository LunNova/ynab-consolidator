import datetime
from pprint import pprint
from typing import List

import fire
from currency_converter import CurrencyConverter

import ynab
from ynab import AccountsApi, BudgetDetailResponse, CategoriesApi, TransactionsApi
from ynab import ApiClient, BudgetsApi, MonthsApi, Account, BudgetDetail


def make_prefix(budget_name: str):
    parts = budget_name.strip().split()
    if len(parts) == 1:
        return f"{budget_name} "
    return f"{''.join([word[0] for word in parts])} "


class Client:
    def __init__(self, api_key):
        configuration = ynab.Configuration()
        configuration.api_key["Authorization"] = api_key
        # Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
        configuration.api_key_prefix["Authorization"] = "Bearer"
        self.configuration = configuration
        self.client = ApiClient(configuration)

    def consolidate(self, source_budgets: List[str], dest_budget: List[str]):
        print("Args:")
        pprint(locals())
        conv = CurrencyConverter(
            "https://www.ecb.europa.eu/stats/eurofxref/eurofxref.zip"
        )

        budgets_api = BudgetsApi(self.client)
        accounts_api = AccountsApi(self.client)
        transactions_api = TransactionsApi(self.client)
        months_api = MonthsApi(self.client)
        categories_api = CategoriesApi(self.client)

        today = datetime.datetime.today().date()

        converted_accounts = []
        converted = {}
        budgets: List = budgets_api.get_budgets().data["budgets"]
        for budget_id in source_budgets:
            budget = [x for x in budgets if x["id"] == budget_id][0]
            budget_name = budget["name"]
            currency = budget["currency_format"]["iso_code"]
            accs: List[Account] = accounts_api.get_accounts(budget_id).data["accounts"]
            prefix = make_prefix(budget_name)
            print(f"{budget_name} {currency}")
            for acc in accs:
                if acc["closed"]:
                    continue
                name = acc["name"]
                if not prefix in name:
                    name = prefix + name
                bal = acc["balance"]
                conv_bal = int(round(conv.convert(bal, currency, "USD")))
                rate = 0 if bal == 0 else conv_bal / bal
                print(f"\t{name} {conv_bal/1000}")
                converted[name.lower()] = (conv_bal, bal, currency, rate)

        category_id = categories_api.get_categories(dest_budget).data[
            "category_groups"
        ][0]["categories"][0]["id"]

        done_accs: List[str] = []

        accs: List[Account] = accounts_api.get_accounts(dest_budget).data["accounts"]
        for acc in accs:
            name = acc["name"]
            balance = acc["balance"]
            if name.lower() not in converted:
                print(f"Can't find budget {name}, skipping")
                continue

            done_accs.append(name.lower())
            target_bal, orig_bal, currency, rate = converted[name.lower()]
            if int(target_bal) == int(balance):
                continue
            print(f"Updating {name} to {target_bal}")
            tran = {
                "account_id": acc["id"],
                "date": today.isoformat(),
                "amount": target_bal - balance,
                "memo": f"{orig_bal/1000} {currency} @ {round(rate, 3)}",
                "approved": True,
                "payee_id": None,
                "payee_name": None,
                "category_id": category_id,
                "cleared": "cleared",
            }
            transactions_api.create_transaction({"transaction": tran}, dest_budget)

        missing_accs_in_dest = [key for key in converted.keys() if key not in done_accs]
        if len(missing_accs_in_dest) > 0:
            missing_accs_output = "', '".join(missing_accs_in_dest)
            print(f"Missing accounts: '{missing_accs_output}'")


if __name__ == "__main__":
    fire.Fire(Client)
