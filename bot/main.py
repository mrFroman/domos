from flask import Flask, request, jsonify
from yookassa import Payment
from yookassa import Configuration

# Используем относительный импорт для Docker
try:
    from bot.tgbot.databases.pay_db import *
except ImportError:
    from tgbot.databases.pay_db import *

app = Flask(__name__)

apikey = 'yaqhMnzvskIsyqjzzxahaXm'
Configuration.configure('960954', 'live_NVL6L_h5QV6BlKN1IVTaBrRzfhX3n4nHSDJ9y2DHSi8')


def genPaymentYookassa(price, desc, fullname):
    number = (getPaymentCount() + 1)
    res = Payment.create(
        {
            "amount": {
                "value": price,
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": "https://merchant-site.ru/return_url"
            },
            "capture": True,
            "description": f'Покупка подписки {fullname}',
            "metadata": {
                'orderNumber': f'{number+550}',
            },
            "receipt": {
                "customer": {
                    "full_name": "Тест Тестович",
                    "email": "example@mail.ru",
                    "phone": "0000000",
                    "inn": "661403691325"
                },
                "items": [
                    {
                        "description":desc,
                        "quantity": "1.00",
                        "amount": {
                            "value": price,
                            "currency": "RUB"
                        },
                        "vat_code": "2",
                        "payment_mode": "full_payment",
                        "payment_subject": "commodity",
                        "country_of_origin_code": "RU",
                        "product_code": "44 4D 01 00 21 FA 41 00 23 05 41 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 12 00 AB 00",
                        "customs_declaration_number": "10714040/140917/0090376",
                        "excise": "20.00",
                        "supplier": {
                            "name": "string",
                            "phone": "string",
                            "inn": "string"
                        }
                    },
                ]
            }
        }
    )
    
    payment_id = res.id
    payment_link = f'https://yoomoney.ru/checkout/payments/v2/contract?orderId={payment_id}'
    print(payment_id)
    print(payment_link)
    return payment_id, payment_link

@app.route('/api', methods=['POST'])
def api():
    req_data = request.get_json()
    print(f'Начинка реквеста: {req_data}\n\n')
    # Проверка apikey
    if 'apikey' not in req_data or req_data['apikey'] != apikey:
        return jsonify({'error': 'Неверный API ключ'}), 401

    # Проверка наличия параметра method
    if 'method' not in req_data:
        return jsonify({'error': 'Отсутствует параметр method'}), 400

    method = req_data['method']
    # Добавьте здесь свою логику обработки запроса в зависимости от значения параметра method
    # Например:
    if method == 'getAllUsers':
            users = getAllUsersForApi()
            user_list = []
            for user in users:
                user_dict = {
                    "user_id": user[0],
                    "pay_status": user[1],
                    "last_pay": user[2],
                    "rank": user[3],
                    "end_pay": user[4],
                    "fullName": user[5],
                    "banned": user[6]
                }
                user_list.append(user_dict)
            return jsonify(user_list)
    
    if method == 'getAllPayments':
            payments = getAllPaymentsForApi()
            payments_list = []
            for payment in payments:
                user_dict = {
                    "user_id": payment[0],
                    "payment_id": payment[1],
                    "amount": payment[2],
                    "ts": payment[3],
                    "status": payment[4],
                }
                payments_list.append(user_dict)
            return jsonify(payments_list)

    if method == 'editUser':
            user = req_data['userid']
            paramToEdit = req_data['param']
            newParam = req_data['newParam']
            changeSomeUserParam(user, paramToEdit, newParam)
            return jsonify({'success': f'Параметр {paramToEdit} для пользователя {user} успешно изменен на {newParam}'})
    
    if method == 'banUser':
            user = req_data['userid']
            paramToEdit = 'banned'
            newParam = 1
            changeSomeUserParam(user, paramToEdit, newParam)
            return jsonify({'success': f'Пользователь {user} забанен!'})
    
    if method == 'unbanUser':
            user = req_data['userid']
            paramToEdit = 'banned'
            newParam = 0
            changeSomeUserParam(user, paramToEdit, newParam)
            return jsonify({'success': f'Пользователь {user} раззабанен!'})
    
    if method == 'createPayment':
            user = req_data['userid']
            amount = req_data['amount']
            fullName = req_data['fullName']
            payment_id, payment_link = genPaymentYookassa(amount, 'Покупка подписки', fullName)
            createPayment(payment_id, amount, user)
            return jsonify({'success': f'Ссылка на оплату успешно создана',
                            'amount': amount,
                            'user_id': user,
                            'link': payment_link,
                            'payment_id': payment_id})

    if method == 'makePayComplete':
            payid = req_data['payment_id']
            makePaymentCompleted(payid)
            return jsonify({'success': f'Счет {payid} отмечен успешным!'})

    else:
        return jsonify({'error': 'Неизвестный метод'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6000)

