import requests, time, random, threading, json, os
from datetime import datetime, timedelta

TOKEN = "8937130532:AAERqXkHVVhG4PONFBvbMZBNMRfE2rOAP2E"
ADMIN_ID = 8885631147
URL = "https://api.telegram.org/bot" + TOKEN + "/"

DIR = os.path.dirname(os.path.abspath(__file__))
F_ORD = os.path.join(DIR, "orders.json")
F_USR = os.path.join(DIR, "users.json")
F_ST  = os.path.join(DIR, "states.json")

orders = {}
users = {}
states = {}


def load(p, d):
    try:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return d


def save(p, d):
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except:
        pass


def s_ord(): save(F_ORD, orders)
def s_usr(): save(F_USR, users)
def s_st():  save(F_ST, states)


def api(method, data=None, quiet=False):
    try:
        if not quiet:
            print("-> " + method)
        r = requests.post(URL + method, json=data, timeout=(10, 40))
        if not quiet:
            print("<- " + str(r.status_code))
        return r.json()
    except Exception as e:
        if not quiet:
            print("!! " + method + ": " + str(e))
        return None


def sm(chat, text, kb=None):
    d = {"chat_id": chat, "text": text, "parse_mode": "HTML"}
    if kb: d["reply_markup"] = kb
    return api("sendMessage", d)


def em(chat, mid, text, kb=None):
    d = {"chat_id": chat, "message_id": mid, "text": text, "parse_mode": "HTML"}
    if kb: d["reply_markup"] = kb
    return api("editMessageText", d)


def ac(cb, text=None, alert=False):
    d = {"callback_query_id": cb}
    if text:
        d["text"] = text
        d["show_alert"] = alert
    return api("answerCallbackQuery", d, quiet=True)


def oid():
    return str(random.randint(1000000000, 9999999999))


def ref_code(uid):
    return "ref" + str(uid % 1000000) + str(random.randint(100, 999))


def is_prem(uid):
    u = users.get(str(uid))
    if not u: return False
    until = u.get("premium_until")
    if not until: return False
    try:
        return datetime.strptime(until, "%d.%m.%Y %H:%M") > datetime.now()
    except:
        return False


def add_prem(uid, days):
    k = str(uid)
    if k not in users:
        users[k] = {"ref_code": ref_code(int(uid)), "invited_by": None, "invited": [], "premium_until": None}
    cur = users[k].get("premium_until")
    try:
        base = datetime.strptime(cur, "%d.%m.%Y %H:%M") if cur else datetime.now()
        if base < datetime.now():
            base = datetime.now()
    except:
        base = datetime.now()
    new = base + timedelta(days=days)
    users[k]["premium_until"] = new.strftime("%d.%m.%Y %H:%M")
    s_usr()
    return new


def kb_main(is_admin=False, uid=None):
    b = [
        [{"text": "Профиль", "callback_data": "profile"},
         {"text": "Покупка Premium Kofi", "callback_data": "buy_premium"}],
        [{"text": "Реферальная система", "callback_data": "referral"}],
    ]
    if uid and is_prem(uid):
        b.append([{"text": "Моя подписка", "callback_data": "my_sub"}])
    if is_admin:
        b.append([{"text": "Панель Админа", "callback_data": "admin_panel"}])
    return {"inline_keyboard": b}


def kb_dur():
    ds = [("1 день","1d"),("3 дня","3d"),("7 дней","7d"),("1 месяц","1m"),
          ("3 месяца","3m"),("6 месяцев","6m"),("1 год","1y"),("2 года","2y")]
    return {"inline_keyboard": [[{"text": l, "callback_data": "buy_" + k}] for l, k in ds]}


def kb_hist(uid):
    uo = {i: o for i, o in orders.items() if str(o["user_id"]) == str(uid)}
    b = []
    for i, o in uo.items():
        st = o.get("status", "Ожидает")
        b.append([{"text": "#" + i + " - " + o["duration"] + " - " + st, "callback_data": "order_" + i}])
    if not b:
        b = [[{"text": "Заказов нет", "callback_data": "noop"}]]
    return {"inline_keyboard": b}


def kb_admin():
    b = []
    so = sorted(orders.items(), key=lambda x: x[1].get("created_at", ""), reverse=True)
    for i, o in so:
        mark = "?" if o.get("status") == "Ожидает" else ("+" if "Принят" in o.get("status", "") else "-")
        b.append([{"text": mark + " #" + i + " - " + o["user_name"] + " - " + o["duration"], "callback_data": "adm_" + i}])
    if not b:
        b = [[{"text": "Заказов пока нет", "callback_data": "noop"}]]
    b.append([{"text": "Обновить", "callback_data": "admin_panel"}])
    return {"inline_keyboard": b}


def kb_adm_ord(i):
    return {"inline_keyboard": [
        [{"text": "Принять", "callback_data": "acc_" + i}],
        [{"text": "Отклонить", "callback_data": "rej_" + i}],
        [{"text": "Написать клиенту", "callback_data": "msg_" + i}],
        [{"text": "Назад", "callback_data": "admin_panel"}],
    ]}


def reg(uid, un, fn):
    k = str(uid)
    if k not in users:
        users[k] = {"ref_code": ref_code(int(uid)), "invited_by": None, "invited": [],
                    "premium_until": None, "username": un or "—", "first_name": fn or "User"}
        s_usr()


def do_ref(new_uid, code):
    if not code: return
    nk = str(new_uid)
    for k, u in users.items():
        if u.get("ref_code") == code and k != nk:
            if users.get(nk, {}).get("invited_by"): return
            users[nk]["invited_by"] = k
            if nk not in u["invited"]:
                u["invited"].append(nk)
            s_usr()
            sm(int(k), "По вашей ссылке зарегистрировался новый пользователь!\nВсего приглашено: " + str(len(u["invited"])) + "\nДо премиума: " + str(max(0, 2 - len(u["invited"]))) + " чел.")
            check_bonus(k)
            return


def check_bonus(k):
    u = users.get(k)
    if not u: return
    n = len(u.get("invited", []))
    if n >= 2 and not u.get("bonus_given"):
        add_prem(int(k), 7)
        u["bonus_given"] = True
        s_usr()
        sm(int(k), "Бонус получен!\nВы пригласили 2 друзей и получаете 7 дней Premium Kofi бесплатно!")


def h_msg(m):
    chat = m["chat"]["id"]
    uid = m["from"]["id"]
    txt = m.get("text", "")
    name = m["from"].get("first_name", "User")
    un = m["from"].get("username")

    if txt.startswith("/start"):
        parts = txt.split(" ", 1)
        code = parts[1] if len(parts) > 1 else None
        new = str(uid) not in users
        reg(uid, un, name)
        if new and code:
            do_ref(uid, code)
        sm(chat, "Привет " + name + "! Это бот для мессенджера Kofi.\nЗдесь ты можешь взаимодействовать со своим профилем",
           kb_main(uid == ADMIN_ID, uid))
        return

    if txt.startswith("/send") and uid == ADMIN_ID:
        p = txt.split(" ", 2)
        if len(p) < 3:
            sm(chat, "Формат: /send USER_ID текст")
            return
        try:
            tu = int(p[1])
            sm(tu, "Сообщение от администратора:\n\n" + p[2])
            sm(chat, "Отправлено")
        except Exception as e:
            sm(chat, "Ошибка: " + str(e))
        return

    if uid in states and states[uid].get("state") == "wait_msg":
        tu = states[uid]["target"]
        sm(tu, "Сообщение от администратора:\n\n" + txt)
        sm(chat, "Сообщение отправлено клиенту!")
        del states[uid]
        s_st()
        return


def h_cb(c):
    cid = c["id"]
    chat = c["message"]["chat"]["id"]
    mid = c["message"]["message_id"]
    uid = c["from"]["id"]
    d = c["data"]
    name = c["from"].get("first_name", "User")

    if d == "profile":
        u = c["from"]
        uo = [o for o in orders.values() if str(o["user_id"]) == str(u["id"])]
        pr = is_prem(u["id"])
        rc = len(users.get(str(u["id"]), {}).get("invited", []))
        t = ("Профиль\n\nИмя: " + u.get("first_name", "") + " " + u.get("last_name", "") +
             "\nUsername: @" + u.get("username", "—") +
             "\nID: <code>" + str(u["id"]) + "</code>" +
             "\nPremium: " + ("Активен" if pr else "Нет") +
             "\nЗаказов: " + str(len(uo)) +
             "\nПриглашено: " + str(rc))
        em(chat, mid, t, {"inline_keyboard": [[{"text": "Назад", "callback_data": "back"}]]})
        ac(cid)

    elif d == "referral":
        k = str(uid)
        u = users.get(k, {})
        rc = u.get("ref_code", "")
        inv = u.get("invited", [])
        info = api("getMe", quiet=True)
        bn = info.get("result", {}).get("username", "") if info else ""
        link = "https://t.me/" + bn + "?start=" + rc if bn else rc
        t = ("Реферальная система\n\nПригласи 2 друзей - получи 7 дней Premium Kofi бесплатно!\n\n"
             "Приглашено: " + str(len(inv)) + " / 2\n"
             "Бонус: " + ("Получен" if u.get("bonus_given") else "Не получен") +
             "\n\nВаша ссылка:\n<code>" + link + "</code>\n\nОтправь её другу - он должен нажать /start в боте.")
        em(chat, mid, t, {"inline_keyboard": [[{"text": "Назад", "callback_data": "back"}]]})
        ac(cid)

    elif d == "my_sub":
        if not is_prem(uid):
            ac(cid, "У вас нет активной подписки", True)
            return
        u = users.get(str(uid), {})
        until = u.get("premium_until", "—")
        try:
            dt = datetime.strptime(until, "%d.%m.%Y %H:%M")
            left = (dt - datetime.now()).days
            t = ("Моя подписка Premium Kofi\n\nСтатус: Активна\nДействует до: " + until +
                 "\nОсталось дней: " + str(max(0, left)) + "\n\nСпасибо, что вы с нами!")
        except:
            t = "Моя подписка\n\nАктивна до: " + until
        em(chat, mid, t, {"inline_keyboard": [[{"text": "Назад", "callback_data": "back"}]]})
        ac(cid)

    elif d == "buy_premium":
        em(chat, mid, "Покупка Kofi Premium\n\nВыбери длительность подписки:", kb_dur())
        ac(cid)

    elif d.startswith("buy_"):
        k = d.replace("buy_", "")
        dm = {"1d":"1 день","3d":"3 дня","7d":"7 дней","1m":"1 месяц",
              "3m":"3 месяца","6m":"6 месяцев","1y":"1 год","2y":"2 года"}
        if k not in dm:
            ac(cid, "Неверный выбор")
            return
        dur = dm[k]
        i = oid()
        u = c["from"]
        orders[i] = {"user_id": u["id"],
                     "user_name": (u.get("first_name", "") + " " + u.get("last_name", "")).strip(),
                     "username": u.get("username", "—"),
                     "duration": dur, "status": "Ожидает",
                     "created_at": datetime.now().strftime("%d.%m.%Y %H:%M")}
        s_ord()
        em(chat, mid, "Заказ создан!\n\nНомер заказа: <code>" + i + "</code>\nДлительность: " + dur +
           "\nСтатус: Ожидает подтверждения",
           {"inline_keyboard": [[{"text": "История заказов", "callback_data": "history"}],
                                 [{"text": "Главное меню", "callback_data": "back"}]]})
        sm(ADMIN_ID, "Новый заказ #" + i + "\n\nКлиент: " + orders[i]["user_name"] +
           "\nUsername: @" + orders[i]["username"] + "\nID: <code>" + str(u["id"]) + "</code>" +
           "\nДлительность: " + dur + "\nДата: " + orders[i]["created_at"], kb_adm_ord(i))
        ac(cid)

    elif d == "history":
        em(chat, mid, "История заказов", kb_hist(uid))
        ac(cid)

    elif d.startswith("order_"):
        i = d.replace("order_", "")
        o = orders.get(i)
        if not o:
            ac(cid, "Заказ не найден")
            return
        em(chat, mid, "Заказ #" + i + "\n\nДлительность: " + o["duration"] +
           "\nСтатус: " + o["status"] + "\nДата: " + o["created_at"],
           {"inline_keyboard": [[{"text": "Назад", "callback_data": "history"}]]})
        ac(cid)

    elif d == "admin_panel":
        if uid != ADMIN_ID:
            ac(cid, "Нет доступа", True)
            return
        total = len(orders)
        pend = sum(1 for o in orders.values() if o.get("status") == "Ожидает")
        em(chat, mid, "Панель Админа\n\nВсего заказов: " + str(total) + "\nОжидают: " + str(pend) +
           "\n\nВыбери заказ:", kb_admin())
        ac(cid)

    elif d.startswith("adm_"):
        if uid != ADMIN_ID:
            ac(cid, "Нет доступа", True)
            return
        i = d.replace("adm_", "")
        o = orders.get(i)
        if not o:
            ac(cid, "Заказ не найден")
            return
        em(chat, mid, "Заказ #" + i + "\n\nКлиент: " + o["user_name"] + "\nUsername: @" + o["username"] +
           "\nID: <code>" + str(o["user_id"]) + "</code>" + "\nДлительность: " + o["duration"] +
           "\nДата: " + o["created_at"] + "\nСтатус: " + o["status"], kb_adm_ord(i))
        ac(cid)

    elif d.startswith("acc_"):
        if uid != ADMIN_ID:
            ac(cid, "Нет доступа", True)
            return
        i = d.replace("acc_", "")
        if i in orders:
            orders[i]["status"] = "Принят"
            s_ord()
            dd = {"1 день":1,"3 дня":3,"7 дней":7,"1 месяц":30,"3 месяца":90,
                  "6 месяцев":180,"1 год":365,"2 года":730}
            add_prem(orders[i]["user_id"], dd.get(orders[i]["duration"], 7))
            sm(orders[i]["user_id"], "Ваш заказ #" + i + " принят!\nPremium активирован на " + orders[i]["duration"],
               {"inline_keyboard": [[{"text": "Моя подписка", "callback_data": "my_sub"}]]})
            ac(cid, "Заказ принят")
            api("editMessageReplyMarkup", {"chat_id": chat, "message_id": mid,
                "reply_markup": {"inline_keyboard": []}}, quiet=True)
            sm(chat, "Заказ #" + i + " принят!")

    elif d.startswith("rej_"):
        if uid != ADMIN_ID:
            ac(cid, "Нет доступа", True)
            return
        i = d.replace("rej_", "")
        if i in orders:
            orders[i]["status"] = "Отклонён"
            s_ord()
            sm(orders[i]["user_id"], "Ваш заказ #" + i + " отклонён.")
            ac(cid, "Заказ отклонён")
            api("editMessageReplyMarkup", {"chat_id": chat, "message_id": mid,
                "reply_markup": {"inline_keyboard": []}}, quiet=True)
            sm(chat, "Заказ #" + i + " отклонён!")

    elif d.startswith("msg_"):
        if uid != ADMIN_ID:
            ac(cid, "Нет доступа", True)
            return
        i = d.replace("msg_", "")
        o = orders.get(i)
        if o:
            states[uid] = {"state": "wait_msg", "target": o["user_id"]}
            s_st()
            sm(chat, "Напиши сообщение клиенту (ID: <code>" + str(o["user_id"]) + "</code>) следующим сообщением.")
        ac(cid)

    elif d == "back":
        em(chat, mid, "Привет " + name + "! Это бот для мессенджера Kofi.\nЗдесь ты можешь взаимодействовать со своим профилем",
           kb_main(uid == ADMIN_ID, uid))
        ac(cid)

    elif d == "noop":
        ac(cid)


def loop():
    off = 0
    print("Бот запущен")
    err = 0
    while True:
        try:
            r = api("getUpdates", {"offset": off, "timeout": 10})
            if r and r.get("ok"):
                err = 0
                for u in r.get("result", []):
                    off = u["update_id"] + 1
                    try:
                        if "message" in u:
                            h_msg(u["message"])
                        elif "callback_query" in u:
                            h_cb(u["callback_query"])
                    except Exception as e:
                        print("Ошибка обработки: " + str(e))
                time.sleep(0.5)
            else:
                err += 1
                w = min(2 ** err, 30)
                print("Пауза " + str(w))
                time.sleep(w)
        except KeyboardInterrupt:
            print("Остановлен")
            break
        except Exception as e:
            err += 1
            w = min(2 ** err, 30)
            print("Ошибка цикла: " + str(e) + ". Пауза " + str(w))
            time.sleep(w)


if __name__ == "__main__":
    orders = load(F_ORD, {})
    users = load(F_USR, {})
    states = load(F_ST, {})
    print("Загружено заказов: " + str(len(orders)) + ", пользователей: " + str(len(users)))
    t = threading.Thread(target=loop, daemon=True)
    t.start()
    print("Бот запущен в фоновом режиме.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Программа завершена.")