from flask import Flask, request, jsonify
import psycopg2
import os
import requests
import logging

app = Flask(__name__)
ROBLOX_COOKIE = os.getenv("ROBLOX_COOKIE", "A8ADA607AB2BE33E0956026E99485D637959690B8B0323A61A8B7634884111D9963EC785A47B557FEEEE5F4B53030D4895DA180091FE3745B10F0EA6DDCEAF58E18758E31A90825B6EA8FFA721DCF73ED82B0A9C56654FCF9EB41CF0C024B2C16CF9D259D5B9AFAEFC4C3EE29C3A0DF5C6B47989B41B2980326EBA867A18B229C34FCC0E34AFC23A97CF7E6A53642AE27296AFD56B0636F653403F2D6E75F6AC50483C259CCB8995E609BA4A5965EFB745BF829F1AD047853028F3B268054EA94807C18BD7669482B1BF686634056412DADFF4849DBF9EBBFE2547A1A6B79547B4C4841E6427851E82F849840B08E73420B6D65FB8C1538D7784DF9B0B91E38AB8E8BBA0906A499903C58A17D4EEEC238808B2C413F37F1A3004838152B8A2E5E9CA0E07B168B58FFCEF6223FDEC04669AF1C07B01FBC244AA92BDAF70C23937F66989DA7E924DAAFC29B709D88FD0DCEB5B687306EF2B6335BCDAA334C10905C63ECFAECB05312239889A403CCB76D7542EA8F885B1F3A596AD328382EF739628A392B81EF841107D79E9A25A328EAF8006AB66A56F0C418F9541AD00CB88D4663080689955C3CE261C786E659389542F329B092CFC591B60B62245DA22D2F2AD24FBCD2796CDE3EEB9577018D2DF245D19D9E4EAA5903397758738FD1153A182CD6259E2276318F296A564107F7056916D4861362702E071D37A0D0EA06DC79511A6CCEEF06FD9EF224D83FDF093D0AAB750B8D0872F27EC9303CF5B0277CFA4AC2F3B2961407ECE387E288681A7144DCCB610A111B7B790D0928DFC49D9B47D0AEA1BEAC6E25FFE8EB27431E58F2EAE243AF152EA4203C953BA94A68EE69198CF4AEF7BA033E3C46F930E7E24720CFC0670B08B1FA1E24C86AB65288365987444B58989487258B0DD2889BD4BD69670BDC951B5451C275BD01BB36CB1E58FD49E75543C20AB758084887DBA0284AE2903A8C7D584DB7B02459416D696AC84B230C895CE022FCFA3A43FCB086F6AB849C521C78BF8E627DD50F93ADF9AE5E011B92F01F85E09524483102D63D5106A9AABA1B038BFAC1065A6D872B734A7DF12E31B41DD3CF614F912005BECEF18F97F94CD2E3048D4B34ED0ED6E422609E58334F4B")
DB_CONN = os.getenv("DATABASE_URL")
GROUPS = {
    "mainGroup": "32886456",
    "party": "32700706",
    "police": "32701182",
    "military": "32830355"
}
logging.basicConfig(level=logging.INFO)

if not DB_CONN:
    raise ValueError("DATABASE_URL not set in environment variables")

def get_db_connection():
    return psycopg2.connect(DB_CONN)

def init_db():
    app.logger.info("Data Base Creating")
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS players (
        userid TEXT PRIMARY KEY,
        politicalpower INTEGER DEFAULT 0,
        militaryexperience INTEGER DEFAULT 0,
        policeauthority INTEGER DEFAULT 0,
        todayplaytime INTEGER DEFAULT 0,
        cycleindex INTEGER DEFAULT 1,
        timelastcheck INTEGER DEFAULT 0,
        timelastreset INTEGER DEFAULT 0,
        pointmultiplier INTEGER DEFAULT 1
    )''')
    conn.commit()
    conn.close()

init_db()

partyRanks = [
    ("99362899", 1),  # PM
    ("99759441", 2),  # PC
    ("99759446", 10), # PB
    ("99759448", 20), # BS
    ("99759449", 35), # PS
    ("107389287", 45), # Party Committee
    ("356554074", 65)  # PSA
]

militaryRanks = [
    ("100066428", 1),  # Private
    ("100066486", 2),  # Corporal
    ("100066487", 7),  # JS
    ("100066489", 15), # Sergeant
    ("100066495", 35), # SS
    ("100066500", 50), # SM
    ("100066501", 70), # JL
    ("100066503", 80), # Lieutenant
    ("100066509", 100), # SL
    ("100066514", 115) # Captain
]

policeRanks = [
    ("99365640", 1),  # Cadet
    ("347256014", 2),  # Junior Militiaman
    ("346316041", 7),  # Militiaman
    ("100026044", 15), # Senior Militiaman
    ("100026045", 35), # Subunit Leader
    ("100026046", 50), # Sergeant Major
    ("100026047", 70), # Junior Lieutenant
    ("100026053", 80), # Lieutenant
    ("107041293", 100), # Senior Lieutenant
    ("100026067", 115) # Captain
]

generalRanks = {
    "military": [
        ("100366937", 1),   # Armed Forces Enlisted
        ("100366954", 15),  # Armed Forces Officer
        ("100366960", 100)  # Armed Forces Leadership
    ],
    "police": [
        ("328484011", 1),   # Law Enforcement Enlisted
        ("100026047", 15),  # Law Enforcement Officer
        ("100026053", 70)   # Law Enforcement Leadership
    ],
    "party": [
        ("100366970", 1),   # Ministry Employee
        ("100366976", 10),  # Ministry Officer
        ("100366986", 45)   # Ministry Leadership
    ]
}

def get_policeRanks(points):
    for rank, threshold in reversed(policeRanks):
        if points >= threshold:
            return {"rank": rank, "threshold": threshold}
    return {"rank": "99365640", "threshold": 1}

def get_militaryRanks(points):
    for rank, threshold in reversed(militaryRanks):
        if points >= threshold:
            return {"rank": rank, "threshold": threshold}
    return {"rank": "100066428", "threshold": 1}

def get_partyRanks(points):
    for rank, threshold in reversed(partyRanks):
        if points >= threshold:
            return {"rank": rank, "threshold": threshold}
    return {"rank": "99759441", "threshold": 1}

def get_generalRanks(points, system):
    ranks = generalRanks.get(system, generalRanks["military"])  # Default to military if system invalid
    for rank, threshold in reversed(ranks):
        if points >= threshold:
            return {"rank": rank, "threshold": threshold}
    return {"rank": ranks[0][0], "threshold": ranks[0][1]}

def get_xsrf_token():
    session = requests.Session()
    session.cookies[".ROBLOSECURITY"] = ROBLOX_COOKIE
    url = "https://auth.roblox.com/v2/logout"
    response = session.post(url)
    xsrf_token = response.headers.get("x-csrf-token")
    if not xsrf_token:
        raise Exception("Failed to retrieve XSRF token")
    return xsrf_token

def update_roblox_rank(user_id, rank_id, group):
    GROUP_ID = GROUPS[group]
    url = f"https://groups.roblox.com/v1/groups/{GROUP_ID}/users/{user_id}"
    xsrf_token = get_xsrf_token()
    headers = {
        "Cookie": f".ROBLOSECURITY={ROBLOX_COOKIE}",
        "Content-Type": "application/json",
        "X-CSRF-TOKEN": xsrf_token
    }
    data = {"roleId": rank_id}
    session = requests.Session()
    session.cookies[".ROBLOSECURITY"] = ROBLOX_COOKIE
    response = session.patch(url, headers=headers, json=data)
    if response.status_code == 200:
        print(f"Promoted user {user_id} to rank {rank_id} in group {group}")
    else:
        print(f"Failed to promote user {user_id}: {response.text}")
        if response.status_code == 403 and "XSRF" in response.text:
            print("Retrying with a fresh XSRF token...")
            headers["X-CSRF-TOKEN"] = get_xsrf_token()
            response = session.patch(url, headers=headers, json=data)
            if response.status_code == 200:
                print(f"Promoted user {user_id} to rank {rank_id} on retry")
            else:
                print(f"Retry failed: {response.text}")

@app.route('/get_player/<userId>', methods=['GET'])
def get_player(userId):
    print(f"Request: Received get_player request")
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT politicalpower, militaryexperience, policeauthority, todayplaytime, cycleindex, timelastreset, pointmultiplier FROM players WHERE userid = %s", (userId,))
    result = c.fetchone()
    conn.close()
    if result:
        return jsonify({"politicalPower": result[0], "militaryExperience": result[1], "policeAuthority": result[2],
                        "todayPlayTime": result[3], "cycleIndex": result[4], "timeLastReset": result[5], "pointMultiplier": result[6]})
    return jsonify({"politicalPower": 0, "militaryExperience": 0, "policeAuthority": 0,
                    "todayPlayTime": 0, "cycleIndex": 1, "timeLastReset": 0, "pointMultiplier": 1})

    

def get_roblox_rank(user_id, group):
    GROUP_ID = GROUPS.get(group)
    if not GROUP_ID:
        print(f"Invalid group: {group}")
        return None, None
    
    try:
        xsrf_token = get_xsrf_token()
        if not xsrf_token:
            return None, None
        headers = {
            "Cookie": f".ROBLOSECURITY={ROBLOX_COOKIE}",
            "Content-Type": "application/json",
            "X-CSRF-TOKEN": xsrf_token
        }
        session = requests.Session()
        session.cookies[".ROBLOSECURITY"] = ROBLOX_COOKIE
        url = f"https://groups.roblox.com/v1/groups/{GROUP_ID}/users/{user_id}"
        response = session.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            role = data.get("role", {})
            return role.get("rank", 999)
        elif response.status_code == 404:
            print(f"User {user_id} not in group {group}")
            return 999
        elif response.status_code == 403 and "XSRF" in response.text:
            print("Retrying with fresh XSRF token...")
            xsrf_token = get_xsrf_token()
            if xsrf_token:
                headers["X-CSRF-TOKEN"] = xsrf_token
                response = session.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    role = data.get("role", {})
                    return role.get("rank", 999)
        print(f"Failed to fetch rank for UserId: {user_id}, Group: {group}, Status: {response.status_code}, Error: {response.text}")
        return None
    except Exception as e:
        print(f"Error fetching rank for UserId: {user_id}, Group: {group}, Exception: {str(e)}")
        return None


@app.route('/update_player/<userId>/<int:politicalPower>/<int:militaryExperience>/<int:policeAuthority>/<int:todayPlayTime>/<int:cycleIndex>/<int:timeLastCheck>/<int:timeLastReset>/<addType>/<int:pointMultiplier>', methods=['POST'])
def update_player(userId, politicalPower, militaryExperience, policeAuthority, todayPlayTime, cycleIndex, timeLastCheck, timeLastReset, addType, pointMultiplier):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO players (userid, politicalpower, militaryexperience, policeauthority, todayplaytime, cycleindex, timelastcheck, timelastreset, pointmultiplier)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (userid) DO UPDATE
        SET politicalpower = %s, militaryexperience = %s, policeauthority = %s, todayplaytime = %s, cycleindex = %s, timelastcheck = %s, timelastreset = %s, pointmultiplier = %s
    """, (userId, politicalPower, militaryExperience, policeAuthority, todayPlayTime, cycleIndex, timeLastCheck, timeLastReset, pointMultiplier,
          politicalPower, militaryExperience, policeAuthority, todayPlayTime, cycleIndex, timeLastCheck, timeLastReset, pointMultiplier))
    conn.commit()
    conn.close()

    # Update specific group rank if not "general" # get the rank of the player after update and the threshhold for this rank
    specific_rank_info = None
    if addType == "general":
        return jsonify({"Update": "No Point Change"}), 200
    elif addType == "party":
        specific_rank_info = get_partyRanks(politicalPower)
        points = politicalPower
        group = "party"
    elif addType == "military":
        specific_rank_info = get_militaryRanks(militaryExperience)
        points = militaryExperience
        group = "military"
    elif addType == "police":
        specific_rank_info = get_policeRanks(policeAuthority)
        points = policeAuthority
        group = "police"
    else:
        return jsonify({"error": "Invalid addType"}), 400
    
    rank=int(get_roblox_rank(userId, "mainGroup"))
    if (rank>79):
        app.logger.info("Player rank is too high no change")
        return jsonify({"Update": "No Main Group Rank Change"}), 200
    app.logger.info("Player rank in main group change")
        

    
    # Update specific group rank if applicable
    if specific_rank_info:
        rankThreshold = specific_rank_info["threshold"]
        if 0 <= points - rankThreshold < pointMultiplier:
            update_roblox_rank(userId, specific_rank_info["rank"], group)

    # Determine most-played system and update general rank
    points_dict = {
        "party": politicalPower,
        "military": militaryExperience,
        "police": policeAuthority
    }
    highest_system = max(points_dict, key=points_dict.get)
    highest_points = points_dict[highest_system]
    general_rank_info = get_generalRanks(highest_points, highest_system)
    general_rank_threshold = general_rank_info["threshold"]
    if 0 <= highest_points - general_rank_threshold < pointMultiplier:
        update_roblox_rank(userId, general_rank_info["rank"], "mainGroup")

    # Return response
    response = {
        "politicalPower": politicalPower,
        "militaryExperience": militaryExperience,
        "policeAuthority": policeAuthority,
        "todayPlayTime": todayPlayTime,
        "cycleIndex": cycleIndex,
        "pointMultiplier": pointMultiplier,
        "highestSystem": highest_system
    }
    if specific_rank_info:
        response["specificRankId"] = specific_rank_info["rank"]
        response["specificRankThreshold"] = specific_rank_info["threshold"]
    response["generalRankId"] = general_rank_info["rank"]
    response["generalRankThreshold"] = general_rank_info["threshold"]
    return jsonify(response)

@app.route('/get_timeLastCheck/<userId>', methods=['GET'])
def get_timeLastCheck(userId):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT timelastcheck FROM players WHERE userid = %s", (userId,))
    result = c.fetchone()
    conn.close()
    if result:
        return jsonify({"timeLastCheck": result[0]})
    return jsonify({"timeLastCheck": 0})

@app.route('/all_players', methods=['GET'])
def all_players():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM players")
    rows = c.fetchall()
    conn.close()
    players = [{"userId": row[0], "politicalPower": row[1], "militaryExperience": row[2], "policeAuthority": row[3],
                "todayPlayTime": row[4], "cycleIndex": row[5], "timeLastCheck": row[6], "timeLastReset": row[7], "pointMultiplier": row[8]} 
               for row in rows]
    return jsonify(players)
