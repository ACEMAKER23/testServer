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

headers = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}

# Allowed stats for updates
ALLOWED_STATS = {
    "politicalpower", "militaryexperience", "policeauthority",
}

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
        ("324914090", 15),  # Law Enforcement Officer
        ("324358078", 70)   # Law Enforcement Leadership
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


def get_membership_id(user_id, group_id):
    url = f"https://apis.roblox.com/cloud/v2/groups/{group_id}/memberships?filter=user=='users/{user_id}'"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        memberships = data.get("groupMemberships", [])
        if memberships:
            membership_path = memberships[0]["path"]
            membership_id = membership_path.split("/")[-1]
            return membership_id
        else:
            print("❌ User is not a member of the group.")
            return None
    else:
        print(f"❌ Failed to fetch membership. Status: {response.status_code}, Error: {response.text}")
        return None


def update_roblox_rank(user_id, group, target_role_id):
    group_id = GROUPS[group]
    membership_id = get_membership_id(user_id, group_id)
    if not membership_id:
        return False

    patch_url = f"https://apis.roblox.com/cloud/v2/groups/{group_id}/memberships/{membership_id}"
    data = {
        "role": f"groups/{group_id}/roles/{target_role_id}"
    }

    response = requests.patch(patch_url, headers=headers, json=data)

    if response.status_code == 200:
        print(f"✅ Successfully updated user {user_id} to role {target_role_id}")
        return True
    else:
        print(f"❌ Failed to update role. Status: {response.status_code}, Error: {response.text}")
        return False


def get_roblox_rank(user_id, group):
    GROUP_ID = GROUPS[group]
    if not GROUP_ID:
        print(f"❌ Invalid group: {group}")
        return None
    url = f"https://apis.roblox.com/cloud/v2/groups/{GROUP_ID}/memberships?maxPageSize=10&filter=user=='users/{user_id}'"
    try:
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            memberships = data.get("groupMemberships", [])
            if not memberships:
                print(f"⚠️ User {user_id} is not in group {GROUP_ID}")
                return None

            role_path = memberships[0].get("role")
            if not role_path:
                print(f"⚠️ Role not found for user {user_id}")
                return None

            role_id = role_path.split("/")[-1]
            role_url = f"https://apis.roblox.com/cloud/v2/groups/{GROUP_ID}/roles/{role_id}"
            role_response = requests.get(role_url, headers=headers)

            if role_response.status_code != 200:
                print(f"❌ Failed to fetch role data. Status: {role_response.status_code}, Error: {role_response.text}")
                return None

            role_data = role_response.json()
            return role_data.get("rank")

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

    botRank = int(get_roblox_rank("8240319152", group) or 0)
    playerRank = int(get_roblox_rank(userId, group) or 0)
    app.logger.info(f"botRank is {botRank} and playerRank is {playerRank}")
    if botRank >= playerRank:
        rankThreshold = specific_rank_info["threshold"]
        if 0 <= points - rankThreshold < pointMultiplier:
            update_roblox_rank(userId, group, specific_rank_info["rank"])
            app.logger.info(f"Player group rank set to {specific_rank_info['rank']}")
    else:
        app.logger.info("Player GROUP rank is too high, no change")

    app.logger.info(f"bot Rank is {botRank} and player rank is {playerRank}")

    mainRank = int(get_roblox_rank(userId, "mainGroup") or 0)
    botMainRank = int(get_roblox_rank("8240319152", "mainGroup") or 0)
    app.logger.info(f"botMainRank is {botMainRank} and playerMainRank is {mainRank}")
    
    if mainRank >= botMainRank:
        app.logger.info("Player main rank is too high no change")
        return jsonify({"Update": "No Main Group Rank Change"}), 200
    
    points_dict = {
        "party": politicalPower,
        "military": militaryExperience,
        "police": policeAuthority
    }
    highest_system = max(points_dict, key=points_dict.get)
    app.logger.info(f"Most played system is {highest_system}")
    highest_points = points_dict[highest_system]
    app.logger.info(f"Most played system have {highest_points} points")
    general_rank_info = get_generalRanks(highest_points, highest_system)
    general_rank_threshold = general_rank_info["threshold"]
    general_rank=general_rank_info["rank"]
    app.logger.info(f"general_rank_threshold is {general_rank_threshold} and general_rank is {general_rank}")

    if 0 <= highest_points - general_rank_threshold < pointMultiplier:
        update_roblox_rank(userId, "mainGroup", general_rank)
        app.logger.info("Player rank in main group changing")
    else:
        app.logger.info("not enough point for main group changing")

    response = {
        "politicalPower": politicalPower,
        "militaryExperience": militaryExperience,
        "policeAuthority": policeAuthority,
        "pointMultiplier": pointMultiplier,
        "highestSystem": highest_system
    }
    return jsonify(response)


@app.route('/admin/add_stat', methods=['POST'])
def add_stat():
    data = request.get_json()
    auth_token = request.headers.get("Authorization")

    if auth_token != os.getenv("AUTH_TOKEN"):
        return jsonify({"error": "Unauthorized"}), 403
    else: app.logger.info(f"authorized")


    userid = data.get('userid')
    stat = data.get('stat')
    amount = data.get('amount')
    '''
    if not userid or not stat or amount is None:
        return jsonify({"error": "Missing required fields"}), 400

    if stat not in ALLOWED_STATS:
        return jsonify({"error": "Invalid stat name"}), 400

    try:
        amount = int(amount)
    except ValueError:
        return jsonify({"error": "Amount must be an integer"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    # Check if player exists
    cur.execute("SELECT * FROM players WHERE userid = %s", (userid,))
    player_data = cur.fetchone()

    if not player_data:
        cur.close()
        conn.close()
        return jsonify({"error": "Player not found"}), 404

    # Fetch existing stats
    cur.execute("""
        SELECT politicalpower, militaryexperience, policeauthority
        FROM players
        WHERE userid = %s
    """, (userid,))
    result = cur.fetchone()

    political_power = result[0]
    military_experience = result[1]
    police_authority = result[2]

    # Update the appropriate stat
    if stat == "politicalpower":
        political_power += amount
        group = "party"
        specific_rank_info = get_partyRanks(political_power)
    elif stat == "militaryexperience":
        military_experience += amount
        group = "military"
        specific_rank_info = get_militaryRanks(military_experience)
    elif stat == "policeauthority":
        police_authority += amount
        group = "police"
        specific_rank_info = get_policeRanks(police_authority)

    # Save updates to database
    cur.execute("""
        UPDATE players
        SET politicalpower = %s,
            militaryexperience = %s,
            policeauthority = %s
        WHERE userid = %s
    """, (political_power, military_experience, police_authority, userid))
    conn.commit()

    # Assume these helper functions exist:
    # get_roblox_rank(), update_roblox_rank(), get_generalRanks()

    bot_rank = int(get_roblox_rank("8240319152", group) or 0)
    player_rank = int(get_roblox_rank(userid, group) or 0)

    if bot_rank >= player_rank:
        update_roblox_rank(userid, group, specific_rank_info["rank"])

    # Handle main group promotion logic
    points_dict = {
        "party": political_power,
        "military": military_experience,
        "police": police_authority
    }
    highest_system = max(points_dict, key=points_dict.get)
    highest_points = points_dict[highest_system]
    general_rank_info = get_generalRanks(highest_points, highest_system)

    main_rank = int(get_roblox_rank(userid, "mainGroup") or 0)
    bot_main_rank = int(get_roblox_rank("8240319152", "mainGroup") or 0)

    if main_rank < bot_main_rank and highest_points >= general_rank_info["threshold"]:
        update_roblox_rank(userid, "mainGroup", general_rank_info["rank"])

    cur.close()
    conn.close()

    response = {
        "politicalPower": political_power,
        "militaryExperience": military_experience,
        "policeAuthority": police_authority,
        "highestSystem": highest_system
    }

    return jsonify(response), 200
    '''
