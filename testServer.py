from flask import Flask, request, jsonify
import psycopg2
import os
import requests
import logging

app = Flask(__name__)
API_KEY = os.getenv("ROBLOX_API")
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
    c.execute('''
        CREATE TABLE IF NOT EXISTS players (
            userid TEXT PRIMARY KEY,
            
            politicalpower INTEGER DEFAULT 0,
            militaryexperience INTEGER DEFAULT 0,
            policeauthority INTEGER DEFAULT 0,
            
            partyplaytime INTEGER DEFAULT 0,
            militaryplaytime INTEGER DEFAULT 0,
            policeplaytime INTEGER DEFAULT 0,
            
            timelastreset INTEGER DEFAULT 0,
            
            pointmultiplier INTEGER DEFAULT 1
        )
    ''')
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

def update_roblox_rank(user_id, rank_id, group):
    GROUP_ID = GROUPS[group]
    
    url = f"https://apis.roblox.com/groups/v2/groups/{GROUP_ID}/users/{user_id}"

    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }

    data = {
        "roleId": rank_id
    }

    response = requests.patch(url, headers=headers, json=data)

    if response.status_code == 200:
        app.logger.info(f"✅ Promoted user {user_id} to rank {rank_id} in group {group}")
    else:
        app.logger.info(f"❌ Failed to promote user {user_id}: {response.text}")
        app.logger.info(f"Status Code: {response.status_code}")


@app.route('/get_player/<userId>', methods=['GET'])
def get_player(userId):
    app.logger.info(f"Request: Received get_player request")
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT politicalpower, militaryexperience, policeauthority, 
               partyplaytime, militaryplaytime, policeplaytime, timelastreset, pointmultiplier 
        FROM players 
        WHERE userid = %s
    ''', (userId,))
    result = c.fetchone()
    conn.close()

    if result:
        return jsonify({
            "politicalpower": result[0],
            "militaryexperience": result[1],
            "policeauthority": result[2],
            "partyplaytime": result[3],
            "militaryplaytime": result[4],
            "policeplaytime": result[5],
            "timelastreset": result[6],
            "pointmultiplier": result[7]
        })
    else:
        return jsonify({
            "politicalpower": 0,
            "militaryexperience": 0,
            "policeauthority":0,
            "partyplaytime": 0,
            "militaryplaytime": 0,
            "policeplaytime": 0,
            "timelastreset": 0,
            "pointmultiplier": 1
        })

    
def get_roblox_rank(user_id, group):
    GROUP_ID = GROUPS.get(group)
    if not GROUP_ID:
        print(f"❌ Invalid group: {group}")
        return None

    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }

    url = f"https://apis.roblox.com/groups/v2/groups/{GROUP_ID}/users/{user_id}"

    try:
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            role = data.get("role", {})
            return role.get("rank", 999)

        elif response.status_code == 404:
            print(f"⚠️ User {user_id} not in group {group}")
            return 999

        else:
            print(f"❌ Failed to fetch rank for UserId: {user_id}, Group: {group}, Status: {response.status_code}, Error: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Exception fetching rank for UserId: {user_id}, Group: {group}, Exception: {str(e)}")
        return None


@app.route('/update_player/<userId>/<int:politicalPower>/<int:militaryExperience>/<int:policeAuthority>/<int:partyPlayTime>/<int:militaryPlayTime>/<int:policePlayTime>/<int:timeLastReset>/<addType>/<int:pointMultiplier>', methods=['POST'])
def update_player(userId, politicalPower, militaryExperience, policeAuthority, partyPlayTime, militaryPlayTime, policePlayTime, timeLastReset, addType, pointMultiplier):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO players (userid, politicalpower, militaryexperience, policeauthority, partyplaytime, militaryplaytime, policeplaytime, timelastreset, pointmultiplier)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (userid) DO UPDATE
        SET politicalpower = %s, militaryexperience = %s, policeauthority = %s,
            partyplaytime = %s, militaryplaytime = %s, policeplaytime = %s,
            timelastreset = %s, pointmultiplier = %s
    """, (
        userId, politicalPower, militaryExperience, policeAuthority, partyPlayTime, militaryPlayTime, policePlayTime, timeLastReset, pointMultiplier,
        politicalPower, militaryExperience, policeAuthority, partyPlayTime, militaryPlayTime, policePlayTime, timeLastReset, pointMultiplier
    ))
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
    # Update specific group rank if applicable, check the player's rank vs the bot's rank
    botRank=int(get_roblox_rank("8240319152", group))
    playerRank = int(get_roblox_rank(userId, group))
    if (botRank>=playerRank):
        if specific_rank_info:
            rankThreshold = specific_rank_info["threshold"]
            if 0 <= points - rankThreshold < pointMultiplier:
                update_roblox_rank(userId, specific_rank_info["rank"], group)
                app.logger.info(f"Player group rank set to specific_rank_info['rank']")
    else:
        app.logger.info("Player GROUP rank is too high, no change")

    app.logger.info(f"bot Rank is {botRank} and player rank is {playerRank}")
    
    mainRank=int(get_roblox_rank(userId, "mainGroup"))
    
    if (mainRank>=botRank):
        app.logger.info("Player main rank is too high no change")
        return jsonify({"Update": "No Main Group Rank Change"}), 200
    app.logger.info("Player rank in main group change")
  
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
        "pointMultiplier": pointMultiplier,
        "highestSystem": highest_system
    }
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
