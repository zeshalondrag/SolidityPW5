from flask import Flask, request, render_template, redirect, url_for, flash, session
import re
from web3 import Web3, HTTPProvider
from contract_info import abi, contract_address
from web3.middleware import geth_poa_middleware

app = Flask(__name__)

w3 = Web3(HTTPProvider('http://127.0.0.1:8545'))

w3.middleware_onion.inject(geth_poa_middleware, layer=0)
contract = w3.eth.contract(address=contract_address, abi=abi)

def is_strong_password(password):
    if len(password) < 12:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    if not re.search(r'[!@#$%^&*()-+=]', password):
        return False
    return True

def get_estates_info():
    try:
        estates = contract.functions.getEstates().call()
        return estates
    except Exception as e:
        flash(f"Ошибка получения информации о недвижимостях: {e}", 'danger')
        return []

def get_ads_info():
    try:
        ads = contract.functions.getAds().call()
        return ads
    except Exception as e:
        flash(f"Ошибка получения информации о текущих объявлениях: {e}", 'danger')
        return []

def get_balances(account, balance_type):
    try:
        if balance_type == 'account':
            account_balance = w3.eth.get_balance(account)
            account_balance_eth = w3.from_wei(account_balance, 'ether')
            return account_balance_eth
        elif balance_type == 'contract':
            contract_balance = contract.functions.getBalance().call({'from': account})
            contract_balance_eth = w3.from_wei(contract_balance, 'ether')  
            return contract_balance_eth
        else:
            return None, None, "Неверно указан тип баланса"
    except Exception as e:
        return None, None, f"Ошибка получения балансов: {e}"

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    try:
        public_key = request.form['public_key']
        password = request.form['password']
        w3.geth.personal.unlock_account(public_key, password)
        session['public_key'] = public_key
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'Ошибка авторизации: {e}', 'danger')
        return redirect(url_for('index'))

@app.route('/register', methods=['POST'])
def register():
    try:
        password = request.form['password']
        if not is_strong_password(password):
            flash('Пароль слишком слабый. Убедитесь, что он содержит как минимум 12 символов, включая заглавные и строчные буквы, цифры и специальные символы.', 'danger')
            return redirect(url_for('index'))
        account = w3.geth.personal.new_account(password)
        flash(f'Успешная регистрация. Ваш публичный ключ: {account}', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Ошибка регистрации: {e}', 'danger')
        return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'public_key' not in session:
        return redirect(url_for('index'))
    public_key = session['public_key']
    return render_template('index.html', public_key=public_key)

@app.route('/logout')
def logout():
    session.pop('public_key', None)
    return redirect(url_for('index'))

@app.route('/account_balance')
def account_balance():
    if 'public_key' not in session:
        return redirect(url_for('index'))
    public_key = session['public_key']
    balance = get_balances(public_key, 'account')
    return render_template('balance.html', public_key=public_key, balance=balance, balance_type='account')

@app.route('/contract_balance')
def contract_balance():
    if 'public_key' not in session:
        return redirect(url_for('index'))
    public_key = session['public_key']
    balance = get_balances(public_key, 'contract')
    return render_template('balance.html', public_key=public_key, balance=balance, balance_type='contract')

@app.route('/estates_info')
def estates_info():
    estates = get_estates_info()
    return render_template('estates_info.html', estates=estates)

@app.route('/ads_info')
def ads_info():
    ads = get_ads_info()
    return render_template('ads_info.html', ads=ads)

@app.route('/send_eth', methods=['GET', 'POST'])
def send_eth():
    if 'public_key' not in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        public_key = session['public_key']
        try:
            amount_eth = float(request.form['amount'])
            amount_wei = int(amount_eth * 10**18)
            tx_hash = contract.functions.toPay(public_key).transact({
                "from": public_key,
                "value": amount_wei,
            })
            flash(f'Транзакция {tx_hash.hex()} отправлена', 'success')
            return redirect(url_for('dashboard'))
        except ValueError:
            flash('Ошибка: неверное значение', 'danger')
        except Exception as e:
            flash(f'Ошибка отправки эфира: {e}', 'danger')
    return render_template('send_eth.html')

@app.route('/withdraw', methods=['GET', 'POST'])
def withdraw():
    if 'public_key' not in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        public_key = session['public_key']
        try:
            amount_eth = float(request.form['amount'])
            amount_wei = int(amount_eth * 10**18)
            tx_hash = contract.functions.withdraw(amount_wei).transact({
                'from': public_key,
            })
            flash(f"Транзакция {tx_hash.hex()} отправлена", 'success')
            return redirect(url_for('dashboard'))
        except ValueError:
            flash('Ошибка: неверное значение', 'danger')
        except Exception as e:
            flash(f'Ошибка снятия средств: {e}', 'danger')
    return render_template('withdraw.html')

@app.route('/create_estate', methods=['GET', 'POST'])
def create_estate():
    if 'public_key' not in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        public_key = session['public_key']
        try:
            size = int(request.form['size'])
            address = request.form['address']
            es_type = int(request.form['es_type'])
            tx_hash = contract.functions.createEstate(size, address, es_type).transact({
                'from': public_key
            })
            flash(f"Транзакция {tx_hash.hex()} отправлена для создания недвижимости", 'success')
            return redirect(url_for('dashboard'))
        except ValueError:
            flash('Ошибка: неверное значение', 'danger')
        except Exception as e:
            flash(f'Ошибка создания недвижимости: {e}', 'danger')
    return render_template('create_estate.html')

@app.route('/create_ad', methods=['GET', 'POST'])
def create_ad():
    if 'public_key' not in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        public_key = session['public_key']
        try:
            id_estate = int(request.form['id_estate'])
            price_eth = float(request.form['price'])
            price_wei = int(price_eth * 10**18)
            tx_hash = contract.functions.createAd(id_estate, price_wei).transact({
                'from': public_key
            })
            flash(f"Транзакция {tx_hash.hex()} отправлена для создания объявления", 'success')
            return redirect(url_for('dashboard'))
        except ValueError:
            flash('Ошибка: неверное значение', 'danger')
        except Exception as e:
            flash(f'Ошибка создания объявления: {e}', 'danger')
    return render_template('create_ad.html')

@app.route('/buy_estate', methods=['GET', 'POST'])
def buy_estate():
    if 'public_key' not in session:
        return redirect(url_for('index'))
    public_key = session['public_key']
    if request.method == 'POST':
        try:
            id_ad = int(request.form['id_ad'])
            tx_hash = contract.functions.buyEstate(id_ad).transact({
                'from': public_key,
                'value': 0
            })
            flash(f"Транзакция {tx_hash.hex()} отправлена для покупки недвижимости", 'success')
            return redirect(url_for('dashboard'))
        except ValueError:
            flash('Ошибка: неверное значение', 'danger')
        except Exception as e:
            flash(f'Ошибка покупки недвижимости: {e}', 'danger')
    ads = get_ads_info()
    return render_template('buy_estate.html', ads=ads)

@app.route('/update_status', methods=['GET', 'POST'])
def update_status():
    if 'public_key' not in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        public_key = session['public_key']
        try:
            id_estate = int(request.form['id_estate'])
            new_status = int(request.form['new_status'])
            tx_hash = contract.functions.updateEstateStatus(id_estate, bool(new_status)).transact({
                'from': public_key
            })
            flash(f"Transaction {tx_hash.hex()} sent to update estate status", 'success')
            return redirect(url_for('dashboard'))
        except ValueError:
            flash('Error: invalid input', 'danger')
        except Exception as e:
            flash(f'Error updating estate status: {e}', 'danger')
    return render_template('update_status.html')

@app.route('/update_ad_status', methods=['GET', 'POST'])
def update_ad_status():
    if 'public_key' not in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        public_key = session['public_key']
        try:
            id_ad = int(request.form['id_ad'])
            new_status = int(request.form['new_status'])
            tx_hash = contract.functions.updateAdStatus(id_ad, new_status).transact({
                'from': public_key
            })
            flash(f"Transaction {tx_hash.hex()} sent to update advertisement status", 'success')
            return redirect(url_for('dashboard'))
        except ValueError:
            flash('Error: invalid input', 'danger')
        except Exception as e:
            flash(f'Error updating advertisement status: {e}', 'danger')
    return render_template('update_ad_status.html')

if __name__ == '__main__':
    app.run(debug=True)
