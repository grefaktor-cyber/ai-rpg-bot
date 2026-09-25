import sqlite3
from datetime import date

class DB:
    def __init__(self, path="game.db"):
        self.conn = sqlite3.connect(path)
        self._init()

    def _init(self):
        self.conn.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            is_premium INTEGER DEFAULT 0,
            requests_today INTEGER DEFAULT 0,
            last_reset TEXT,
            story TEXT DEFAULT '',
            consent_given INTEGER DEFAULT 0,
            consent_date TEXT,
            referred_by INTEGER DEFAULT 0,
            referral_count INTEGER DEFAULT 0
        )""")
        self.conn.commit()

    def get_user(self, user_id, username=""):
        today = str(date.today())
        c = self.conn.cursor()
        c.execute("""SELECT user_id, username, is_premium, requests_today,
                     last_reset, story, consent_given, referred_by, referral_count
                     FROM users WHERE user_id=?""", (user_id,))
        row = c.fetchone()
        if not row:
            c.execute("""INSERT INTO users (user_id, username, last_reset)
                         VALUES (?,?,?)""", (user_id, username, today))
            self.conn.commit()
            return {"user_id": user_id, "is_premium": 0, "requests_today": 0,
                    "story": "", "consent_given": 0, "referred_by": 0, "referral_count": 0}
        if row[4] != today:
            c.execute("UPDATE users SET requests_today=0, last_reset=? WHERE user_id=?",
                      (today, user_id))
            self.conn.commit()
            return {"user_id": row[0], "is_premium": row[2], "requests_today": 0,
                    "story": row[5], "consent_given": row[6], "referred_by": row[7],
                    "referral_count": row[8]}
        return {"user_id": row[0], "is_premium": row[2], "requests_today": row[3],
                "story": row[5], "consent_given": row[6], "referred_by": row[7],
                "referral_count": row[8]}

    def give_consent(self, user_id):
        self.conn.execute("""UPDATE users SET consent_given=1, consent_date=?
                             WHERE user_id=?""", (str(date.today()), user_id))
        self.conn.commit()

    def revoke_consent(self, user_id):
        self.conn.execute("""UPDATE users SET consent_given=0, story=''
                             WHERE user_id=?""", (user_id,))
        self.conn.commit()

    def set_referrer(self, user_id, referrer_id):
        c = self.conn.cursor()
        c.execute("SELECT referred_by FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        if row and row[0] == 0 and referrer_id != user_id:
            self.conn.execute("UPDATE users SET referred_by=? WHERE user_id=?",
                              (referrer_id, user_id))
            self.conn.execute("""UPDATE users SET referral_count=referral_count+1,
                                 requests_today=requests_today+10
                                 WHERE user_id=?""", (referrer_id,))
            self.conn.commit()
            return True
        return False

    def increment(self, user_id):
        self.conn.execute("UPDATE users SET requests_today=requests_today+1 WHERE user_id=?",
                          (user_id,))
        self.conn.commit()

    def update_story(self, user_id, story):
        self.conn.execute("UPDATE users SET story=? WHERE user_id=?", (story, user_id))
        self.conn.commit()

    def set_premium(self, user_id, value=1):
        self.conn.execute("UPDATE users SET is_premium=? WHERE user_id=?",
                          (value, user_id))
        self.conn.commit()