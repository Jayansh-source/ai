from flask import Flask, request, jsonify, render_template, session, redirect
import os, json, hashlib, requests

app = Flask(__name__, template_folder='.', static_folder='.')
app.secret_key = 'supersecret123'

BASE_URL = "https://wormai.a-lonely-ooo.workers.dev/?prompt="

USERS_FILE = 'users.json'
MEMORY_FOLDER = 'memories'

if not os.path.exists(MEMORY_FOLDER):
    os.makedirs(MEMORY_FOLDER)

# --------- Helper Functions ----------
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE,'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE,'w') as f:
        json.dump(users,f)

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def load_memory(username):
    path = os.path.join(MEMORY_FOLDER,f"{username}.json")
    if os.path.exists(path):
        with open(path,'r') as f:
            return json.load(f)
    return {'messages':[],'message_count':0,'total_chars':0}

def save_memory(username,mem):
    path = os.path.join(MEMORY_FOLDER,f"{username}.json")
    with open(path,'w') as f:
        json.dump(mem,f)

# --------- Routes -----------

@app.route('/')
def index():
    if 'username' in session:
        return render_template('chat.html', username=session['username'])
    return redirect('/login')

# ------ Login Page ------
@app.route('/login', methods=['GET','POST'])
def login_page():
    if request.method=='GET':
        # If already logged in → logout
        if 'username' in session:
            session.pop('username')
        return render_template('login.html')
    else:
        data = request.get_json()
        username = data.get('username','').strip()
        password = data.get('password','').strip()
        users = load_users()
        if username in users and users[username]['password']==hash_password(password):
            session['username']=username
            return jsonify({'status':'success','msg':'Logged in successfully'})
        return jsonify({'status':'error','msg':'Invalid username or password'})

# ------ Register ------
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username','').strip()
    password = data.get('password','').strip()
    fullName = data.get('fullName','').strip()
    email = data.get('email','').strip()
    mobile = data.get('mobile','').strip()
    dob = data.get('dob','').strip()

    users = load_users()
    if username in users:
        return jsonify({'status':'error','msg':'Username already exists'})

    users[username] = {
        'password': hash_password(password),
        'fullName': fullName,
        'email': email,
        'mobile': mobile,
        'dob': dob
    }
    save_users(users)

    # create empty memory
    save_memory(username, {'messages':[],'message_count':0,'total_chars':0})

    session['username']=username
    return jsonify({'status':'success','msg':'Account created successfully'})

# ------ Logout ------
@app.route('/logout')
def logout():
    session.pop('username',None)
    return redirect('/login')

# ------ AI Chat ------
@app.route('/send', methods=['POST'])
def send():
    if 'username' not in session:
        return jsonify({'reply':'Please login first'}),403
    username = session['username']
    data = request.get_json()
    user_msg = data.get('message','').strip()

    mem = load_memory(username)
    mem['messages'].append(f"User: {user_msg}")
    mem['message_count']+=1
    mem['total_chars']+=len(user_msg)

    full_prompt = "\n".join(mem['messages']) + "\nAI:"
    full_url = BASE_URL + requests.utils.quote(full_prompt)

    try:
        resp = requests.get(full_url, timeout=30)
        if resp.status_code==200:
            data = resp.json()
            reply = data.get("response","No response").strip()
        else:
            reply = "Server busy, try later"
    except:
        reply = "Server busy, check connection"

    mem['messages'].append(f"AI: {reply}")
    mem['message_count']+=1
    mem['total_chars']+=len(reply)
    save_memory(username, mem)

    return jsonify({'reply':reply})

# ------ Clear Memory ------
@app.route('/clear_memory', methods=['POST'])
def clear_memory_route():
    if 'username' not in session:
        return jsonify({'status':'error','msg':'Login first'}),403
    save_memory(session['username'], {'messages':[],'message_count':0,'total_chars':0})
    return jsonify({'status':'success','msg':'Memory cleared'})

# ------ Get Memory Stats ------
@app.route('/get_memory_stats')
def get_memory_stats():
    if 'username' not in session:
        return jsonify({'error':'Login first'}),403
    mem = load_memory(session['username'])
    return jsonify({
        'message_count': mem['message_count'],
        'total_chars': mem['total_chars']
    })

# ------ Delete Account ------
@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'username' not in session:
        return jsonify({'status':'error','msg':'Login first'}),403
    username = session['username']
    users = load_users()
    if username in users:
        users.pop(username)
        save_users(users)
    mem_file = os.path.join(MEMORY_FOLDER,f"{username}.json")
    if os.path.exists(mem_file):
        os.remove(mem_file)
    session.pop('username')
    return jsonify({'status':'success','msg':'Account deleted'})

# ------ Run App ------
if __name__=='__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
