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
    ("99759446", 10),  # PB
    ("99759448", 20),  # BS
    ("99759449", 35),  # PS
    ("107389287", 45),  # Party Committee
    ("356554074", 65)  # PSA
]

militaryRanks = [
    ("100066428", 1),  # Private
    ("100066486", 2),  # Corporal
    ("100066487", 7),  # JS
    ("100066489", 15),  # Sergeant
    ("100066495", 35),  # SS
    ("100066500", 50),  # SM
    ("100066501", 70),  # JL
    ("100066503", 80),  # Lieutenant
    ("100066509", 100),  # SL
    ("100066514", 115)  # Captain
]

policeRanks = [
    ("99365640", 1),  # Cadet
    ("347256014", 2),  # Junior Militiaman
    ("346316041", 7),  # Militiaman
    ("100026044", 15),  # Senior Militiaman
    ("100026045", 35),  # Subunit Leader
    ("100026046", 50),  # Sergeant Major
    ("100026047", 70),  # Junior Lieutenant
    ("100026053", 80),  # Lieutenant
    ("107041293", 100),  # Senior Lieutenant
    ("100026067", 115)  # Captain
]

longIdToShortIdDict = { #hard coded stuff, must be change if the rank in group change
    "99365640": 1,  # Cadet
    "347256014": 2,  # Junior Militiaman
    "346316041": 3,  # Militiaman
    "100026044": 4,  # Senior Militiaman
    "100026045": 5,  # Subunit Leader
    "100026046": 6,  # Sergeant Major
    "100026047": 7,  # Junior Lieutenant
    "100026053": 8,  # Lieutenant
    "107041293": 9,  # Senior Lieutenant
    "100026067": 10,  # Captain

    "100066428": 1,  # Private
    "100066486": 2,  # Corporal
    "100066487": 3,  # JS
    "100066489": 4,  # Sergeant
    "100066495": 5,  # SS
    "100066500": 6,  # SM
    "100066501": 7,  # JL
    "100066503": 8,  # Lieutenant
    "100066509": 9,  # SL
    "100066514": 10,  # Captain

    "99362899": 1,  # PM
    "99759441": 2,  # PC
    "99759446": 3,  # PB
    "99759448": 4,  # BS
    "99759449": 6,  # PS
    "107389287": 10,  # Party Committee
    "356554074": 11   # PSA
}

generalRanks = {
    "military": [
        ("100366937", 1),  # Armed Forces Enlisted
        ("100366954", 70),  # Armed Forces Officer
        ("100366960", 150)  # Armed Forces Leadership
    ],
    "police": [
        ("328484011", 1),  # Law Enforcement Enlisted
        ("324914090", 70),  # Law Enforcement Officer
        ("324358078", 150)  # Law Enforcement Leadership
    ],
    "minstry": [
        ("100366970", 1),  # Ministry Employee
        ("100366976", 66),  # Ministry Officer
        ("100366986", 120)  # Ministry Leadership
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

    if result:
        conn.close()
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
        # Player not found, initialize
        data = initializePlayer(userId, conn)
        conn.commit()
        conn.close()
        return jsonify(data)


def get_rank_points(rankid, rank_list):
    if rankid is None:
        return 1
    for rid, points in rank_list:
        if rid == str(rankid):
            return points
    return max(points for _, points in rank_list)


def initializePlayer(user_id, conn):
    with conn.cursor() as cur:
        # Get player's Roblox group ranks
        party_rank = get_roblox_rank(user_id, "party", "long")
        military_rank = get_roblox_rank(user_id, "military", "long")
        police_rank = get_roblox_rank(user_id, "police", "long")

        # Determine point values
        political_power = get_rank_points(party_rank, partyRanks)
        military_experience = get_rank_points(military_rank, militaryRanks)
        police_authority = get_rank_points(police_rank, policeRanks)

        # Insert into database
        cur.execute("""
            INSERT INTO players (
                userid, politicalpower, militaryexperience, policeauthority,
                partyplaytime, militaryplaytime, policeplaytime,
                timelastreset, pointmultiplier
            ) VALUES (%s, %s, %s, %s, 0, 0, 0, 0, 1)
        """, (
            user_id,
            political_power,
            military_experience,
            police_authority
        ))

    return {
        "politicalpower": political_power,
        "militaryexperience": military_experience,
        "policeauthority": police_authority,
        "partyplaytime": 0,
        "militaryplaytime": 0,
        "policeplaytime": 0,
        "timelastreset": 0,
        "pointmultiplier": 1
    }


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


def get_roblox_rank(user_id, group, t):
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
            if t == "long":
                return role_id
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
            print(
                f"❌ Failed to fetch rank for UserId: {user_id}, Group: {group}, Status: {response.status_code}, Error: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Exception fetching rank for UserId: {user_id}, Group: {group}, Exception: {str(e)}")
        return None


@app.route(
    '/update_player/<userId>/<int:politicalPower>/<int:militaryExperience>/<int:policeAuthority>/<int:partyPlayTime>/<int:militaryPlayTime>/<int:policePlayTime>/<int:timeLastReset>/<addType>/<int:pointMultiplier>',
    methods=['POST'])
def update_player(userId, politicalPower, militaryExperience, policeAuthority, partyPlayTime, militaryPlayTime,
                  policePlayTime, timeLastReset, addType, pointMultiplier):
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
        userId, politicalPower, militaryExperience, policeAuthority, partyPlayTime, militaryPlayTime, policePlayTime,
        timeLastReset, pointMultiplier,
        politicalPower, militaryExperience, policeAuthority, partyPlayTime, militaryPlayTime, policePlayTime,
        timeLastReset, pointMultiplier
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

    botRank = int(get_roblox_rank("8240319152", group, "short") or 0)
    playerRank = int(get_roblox_rank(userId, group, "short") or 0)
    app.logger.info(f"botRank is {botRank} and playerRank is {playerRank}")
    if botRank >= playerRank:
        rankThreshold = specific_rank_info["threshold"]
        if 0 <= points - rankThreshold < pointMultiplier:
            update_roblox_rank(userId, group, specific_rank_info["rank"])
            app.logger.info(f"Player group rank set to {specific_rank_info['rank']}")
    else:
        app.logger.info("Player GROUP rank is too high, no change")

    app.logger.info(f"bot Rank is {botRank} and player rank is {playerRank}")

    mainRank = int(get_roblox_rank(userId, "mainGroup", "short") or 0)
    botMainRank = int(get_roblox_rank("8240319152", "mainGroup", "short") or 0)
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
    general_rank = general_rank_info["rank"]
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
    return jsonify(response), 200


@app.route('/add_point/<userId>/<pointType>/<int:amount>', methods=['POST'])
def addPoint(userId, pointType, amount):
    if pointType not in ['politicalPower', 'militaryExperience', 'policeAuthority']:
        return jsonify({'error': 'Invalid pointType'}), 400

    conn = get_db_connection()
    c = conn.cursor()

    c.execute("SELECT politicalpower, militaryexperience, policeauthority FROM players WHERE userid = %s", (userId,))
    result = c.fetchone()

    if result is None:
        return jsonify({'error': 'User not found'}), 404

    points = {
        'politicalPower': result[0],
        'militaryExperience': result[1],
        'policeAuthority': result[2]
    }

    if pointType == 'politicalPower':
        points[pointType] += amount


    points[pointType] += amount

    c.execute(f"UPDATE players SET {pointType.lower()} = %s WHERE userid = %s", (points[pointType], userId))
    conn.commit()
    conn.close()

    return jsonify({'message': f'{pointType} updated successfully', 'newValue': points[pointType]}), 200


@app.route(
    '/update_metadata/<userId>/<int:partyPlayTime>/<int:militaryPlayTime>/<int:policePlayTime>/<int:timeLastReset>/<int:pointMultiplier>',
    methods=['POST'])
def update_metadata(userId, partyPlayTime, militaryPlayTime, policePlayTime, timeLastReset, pointMultiplier):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO players (userid, partyplaytime, militaryplaytime, policeplaytime, timelastreset, pointmultiplier)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (userid) DO UPDATE
        SET partyplaytime = %s, militaryplaytime = %s, policeplaytime = %s,
            timelastreset = %s, pointmultiplier = %s
    """, (
        userId, partyPlayTime, militaryPlayTime, policePlayTime, timeLastReset, pointMultiplier,
        partyPlayTime, militaryPlayTime, policePlayTime, timeLastReset, pointMultiplier
    ))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Metadata updated successfully'}), 200


@app.route('/get_points/<userId>', methods=['GET'])
def get_points(userId):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT politicalpower, militaryexperience, policeauthority FROM players WHERE userid = %s", (userId,))
    result = c.fetchone()
    conn.close()

    if result is None:
        app.logger.info(f"Not Data returned")
        return jsonify({'error': 'User not found'}), 404
    app.logger.info(f"Data returned, {result[0]}, {result[1]}, {result[2]}")

    return jsonify({'politicalPower': result[0], 'militaryExperience': result[1], 'policeAuthority': result[2]}), 200


@app.route('/admin/add_stat', methods=['POST'])
def add_stat():
    data = request.get_json()
    auth_token = request.headers.get("Authorization")

    if auth_token != os.getenv("AUTH_TOKEN"):
        return jsonify({"error": "Unauthorized"}), 403
    else:
        app.logger.info(f"authorized")

    userid = data.get('userid')
    stat = data.get('stat')
    amount = data.get('amount')

    if not userid or not stat or amount is None:
        return jsonify({"error": "Player Not Found, add the player using add command first"}), 400

    if not userid or not stat or amount is None:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        amount = int(amount)
    except ValueError:
        return jsonify({"error": "Amount must be an integer"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch existing stats
    cur.execute("""
        SELECT politicalpower, militaryexperience, policeauthority
        FROM players
        WHERE userid = %s
    """, (userid,))
    result = cur.fetchone()

    if not result:
        return jsonify({"error": "User doesn't exist in database, add user first"}), 400

    political_power = result[0]
    military_experience = result[1]
    police_authority = result[2]

    player_military_rank = int(get_roblox_rank(userid, "military", "short") or 0) ## old ranks
    player_police_rank = int(get_roblox_rank(userid, "police", "short") or 0)
    player_party_rank = int(get_roblox_rank(userid, "party", "short") or 0)
    player_main_rank = int(get_roblox_rank(userid, "mainGroup", "short") or 0)
    new_player_police_rank = None
    new_player_military_rank = None
    new_player_party_rank = None
    new_player_main_rank = None
    response = {
        "politicalPower": political_power,
        "militaryExperience": military_experience,
        "policeAuthority": police_authority,
        "highestSystem": "unknown",
        "divisionPromotion": "Player Rank Didn't Change",
        "mainPromotion": "Player Rank Didn't Change",
    }

    if stat == "politicalpower":
        political_power += amount
        response["politicalPower"]=political_power
        app.logger.info(f"Changing political power to {political_power}")
        group = "party"
        specific_rank_info = get_partyRanks(political_power)
        rankNumID=longIdToShortIdDict.get(specific_rank_info['rank'], 0)
        app.logger.info(f"Rank {rankNumID} and {specific_rank_info['rank']}")
        if (not rankNumID == player_party_rank) and (rankNumID < bot_party_rank):
            ##new_player_party_rank = int(get_roblox_rank(userid, "party", "short") or 0)
            update_roblox_rank(userid, group, specific_rank_info["rank"])
            response["divisionPromotion"] = f"Player Party Rank Changed to {specific_rank_info['rank']}"
        cur.execute("""
            UPDATE players
            SET politicalpower = %s,
                militaryexperience = %s,
                policeauthority = %s
                WHERE userid = %s
        """, (political_power, military_experience, police_authority, userid))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(response), 200
    elif stat == "militaryexperience":
        military_experience += amount
        response["militaryExperience"] = military_experience
        app.logger.info(f"Changing military experience to {military_experience}")
        group = "military"
        specific_rank_info = get_militaryRanks(military_experience)   ## new rank
        rankNumID = longIdToShortIdDict.get(specific_rank_info['rank'], 0)
        app.logger.info(f"Rank {rankNumID} and {specific_rank_info['rank']}")
        if (not rankNumID == player_military_rank) and (rankNumID < bot_military_rank):
            update_roblox_rank(userid, group, specific_rank_info["rank"])
            response["divisionPromotion" ] = f"Player Military Rank Changed to {specific_rank_info['rank']}"
            new_player_military_rank = int(get_roblox_rank(userid, "military", "short") or 0)
    elif stat == "policeauthority":
        police_authority += amount
        response["policeAuthority"] = police_authority
        app.logger.info(f"Changing police authority to {military_experience}")
        group = "police"
        specific_rank_info = get_policeRanks(police_authority)     ## new rank
        rankNumID = longIdToShortIdDict.get(specific_rank_info['rank'], 0)
        app.logger.info(f"Rank {rankNumID} and {specific_rank_info['rank']}")
        if (not rankNumID == player_police_rank) and (rankNumID < bot_party_rank):
            update_roblox_rank(userid, group, specific_rank_info["rank"])
            response["divisionPromotion"] = f"Player Police Rank Changed to {specific_rank_info['rank']}"
            new_player_police_rank = int(get_roblox_rank(userid, "police", "short") or 0)
    else:
        return jsonify({"error": "Invalid Stat Type"}), 400

    cur.execute("""
        UPDATE players
        SET politicalpower = %s,
            militaryexperience = %s,
            policeauthority = %s
        WHERE userid = %s
    """, (political_power, military_experience, police_authority, userid))
    conn.commit()
    cur.close()
    conn.close()


    if new_player_police_rank:                                          ## police changed
        if 16 >= new_player_police_rank >= 14:
            if player_military_rank <= 13 or player_military_rank >=15:## police crossed the leader, yet military is not already a leader
                if player_main_rank < bot_main_rank and player_main_rank != 73:
                    update_roblox_rank(userid, "mainGroup", "324358078")
                    response["mainPromotion"] = f"Player Police Rank Changed to law enforcement leader"
        elif 7 <= new_player_police_rank <= 13:
            if player_military_rank < 7 or player_military_rank > 13:
                if player_main_rank < bot_main_rank and player_main_rank != 72:
                    update_roblox_rank(userid, "mainGroup", "324914090")
                    response["mainPromotion"] = f"Player Police Rank Changed to law enforcement officer"
        elif 6 >= new_player_police_rank >= 1:
            if player_military_rank > 6 or player_military_rank < 1:
                if player_main_rank < bot_main_rank and player_main_rank != 71:
                    update_roblox_rank(userid, "mainGroup", "328484011")
                    response["mainPromotion"] = f"Player Police Rank Changed to law enforcement enlisted"

    elif new_player_military_rank:
        if 16 >= new_player_military_rank >= 14:
            if player_police_rank < 14:             ## militarty crossed the leader, yet police is not already a leader
                if player_main_rank < bot_main_rank and player_main_rank != 69:
                    update_roblox_rank(userid, "mainGroup", "100366960")
                    response["mainPromotion"] = f"Player Military Rank Changed to military leader"
        elif 13 >= new_player_military_rank >= 7:
            if player_police_rank < 7:
                if player_main_rank < bot_main_rank and player_main_rank != 63:  ## militarty crossed the officer, yet police is not already a officer
                    update_roblox_rank(userid, "mainGroup", "100366954")
                    response["mainPromotion"] = f"Player Military Rank Changed to military officer"
        elif 6 >= new_player_military_rank >= 1:
            if player_police_rank < 1:                                       ## militarty crossed the enlisted, yet police is lower than already a englisted
                if player_main_rank < bot_main_rank and player_main_rank != 61:
                    update_roblox_rank(userid, "mainGroup", "100366937")
                    response["mainPromotion"] = f"Player Military Rank Changed to military enlisted"

    return jsonify(response), 200

@app.route("/admin/add_player", methods=["POST"])
def add_player():
    if request.headers.get("Authorization") != os.getenv("AUTH_TOKEN"):
        return jsonify({"error": "Invalid authorization token"}), 401
    data = request.get_json()
    userid = data.get("userid")
    if not userid:
        return jsonify({"error": "Missing userid"}), 400
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Check if userid already exists
        cur.execute("SELECT userid FROM users WHERE userid = ?", (userid,))
        if cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({"error": "User already exists in the database"}), 409
        # Insert new user with default values
        cur.execute("""
            INSERT INTO users (userid, politicalpower, militaryexperience, policeauthority, partyplaytime, militaryplaytime, policeplaytime, timelastreset, pointmultiplier)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (userid, 0, 0, 0, 0, 0, 0, 0, 1))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"message": f"User {userid} added with default stats"}), 200
    except Exception as e:
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500


bot_military_rank = int(get_roblox_rank("8240319152", "military", "short") or 999)
bot_police_rank = int(get_roblox_rank("8240319152", "police", "short") or 999)
bot_party_rank = int(get_roblox_rank("8240319152", "party", "short") or 999)
bot_main_rank = int(get_roblox_rank("8240319152", "mainGroup", "short") or 999)
