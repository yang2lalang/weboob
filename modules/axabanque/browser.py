# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.


import json

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword

from .pages import KeyboardPage, LoginPage, PredisconnectedPage, BankAccountsPage, \
                   InvestmentActivatePage, InvestmentCguPage, InvestmentPage, \
                   CBTransactionsPage, TransactionsPage, UnavailablePage, IbanPage


class AXABanque(LoginBrowser):
    BASEURL = 'https://www.axabanque.fr/'

    # Login
    keyboard = URL('https://www.axa.fr/.sendvirtualkeyboard.json', KeyboardPage)
    login = URL('https://www.axa.fr/.loginAxa.json', LoginPage)
    predisconnected = URL('https://www.axa.fr/axa-predisconnect.html', PredisconnectedPage)
    # Bank
    bank_accounts = URL('transactionnel/client/liste-comptes.html',
                        'webapp/axabanque/client/sso/connexion\?token=(?P<token>.*)', BankAccountsPage)
    iban_pdf = URL('http://www.axabanque.fr/webapp/axabanque/formulaire_AXA_Banque/.*\.pdf.*', IbanPage)
    cbttransactions = URL('webapp/axabanque/jsp/detailCarteBleu.*.faces', CBTransactionsPage)
    transactions = URL('webapp/axabanque/jsp/panorama.faces',
                       'webapp/axabanque/jsp/detail.*.faces', TransactionsPage)
    unavailable = URL('login_errors/indisponibilite.*',
                      '.*page-indisponible.html.*',
                      '.*erreur/erreurBanque.faces', UnavailablePage)
    # Investment
    investment_activate = URL('https://client.axa.fr/_layouts/NOSI/MonitoringSedia.aspx', InvestmentActivatePage)
    investment_cgu = URL('https://client.axa.fr/_layouts/nosi/CGUPage.aspx', InvestmentCguPage)
    investment = URL('https://client.axa.fr/mes-comptes-et-contrats/Pages/(?P<page>.*)',
                     'https://client.axa.fr/_layouts/NOSI/LoadProfile.aspx',
                     'https://consultations.agipi.com', InvestmentPage)

    def __init__(self, *args, **kwargs):
        super(AXABanque, self).__init__(*args, **kwargs)
        self.tokens = {}
        self.account_pages = {}

    def do_login(self):
        html = json.loads(self.keyboard.go(data={'login': self.username}).content)['html']
        self.page.doc = self.page.build_doc(html.encode('utf-8'))

        data = self.page.get_data(self.username, self.password)
        error = self.login.go(data=data).check_error()

        # Activate tokens if there has
        if self.tokens['bank']:
            error = self.bank_accounts.go(token=self.tokens['bank']).check_error()
        if self.tokens['investment']:
            self.investment_activate.go(data={'tokenmixte': self.tokens['investment']})

        if error:
            raise BrowserIncorrectPassword(error)


    @need_login
    def iter_accounts(self):
        accounts = []
        # Get bank accounts if there has
        if self.tokens['bank']:
            self.transactions.go()
            for a in self.bank_accounts.go().get_list():
                args = a._args
                if a.type == a.TYPE_CHECKING and 'paramCodeFamille' in args:
                    iban_params = {'action': 'RIBCC',
                                   'numCompte': args['paramNumCompte'],
                                   'codeFamille': args['paramCodeFamille'],
                                   'codeProduit': args['paramCodeProduit'],
                                   'codeSousProduit': args['paramCodeSousProduit'],
                                  }
                    r = self.open('https://www.axabanque.fr/webapp/axabanque/popupPDF', params=iban_params)
                    a.iban = r.page.get_iban()
                accounts.append(a)

        # Get investment accounts if there has
        if self.tokens['investment']:
            self.investment_pages = []
            self.investment.go(page="default.aspx").get_home()
            self.investment.go(page="default.aspx")
            # If user has cgu
            if not self.investment_cgu.is_here():
                for form in self.page.get_forms():
                    for a in self.investment.go(page="PartialUpdatePanelLoader.ashx", \
                            data=form).iter_accounts():
                        accounts.append(a)
        return iter(accounts)

    def go_account_pages(self, account):
        if account.id in self.account_pages:
            self.page = self.account_pages[account.id]
        else:
            self.bank_accounts.go()
            args = account._args
            args['javax.faces.ViewState'] = self.page.get_view_state()
            self.transactions.go(data=args)
            self.account_pages[account.id] = self.page

    @need_login
    def iter_investment(self, account):
        if account._acctype is "investment":
            return account._page.iter_investment()
        if account._acctype is "bank" and account._hasinv:
            self.go_account_pages(account)
            return self.page.iter_investment()
        return iter([])

    @need_login
    def iter_history(self, account):
        # Bank's history
        if account._acctype is "bank" and not account._hasinv:
            self.go_account_pages(account)
            if not self.page.more_history():
                return iter([])
            return self.page.get_history()
        # Investment's history
        if account._acctype is "investment":
            return account._page.iter_history()
        return iter([])
