"""
Örnek: demo ve ödev testi için bilinçli olarak ZAYIF kod.
SecureCode Mentor arayüzünde bu dosyayı yükleyip analiz edebilirsin.
"""

import sqlite3


def get_user_by_name(name: str):
    # SQL Injection riski: kullanıcı girdisi sorguya gömülüyor
    conn = sqlite3.connect(":memory:")
    q = "SELECT * FROM users WHERE name = '" + name + "'"
    return conn.execute(q).fetchall()


API_KEY = "sk-test-1234567890abcdefghij"  # hardcoded secret örneği
