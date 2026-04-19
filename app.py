from flask import Flask, request, jsonify, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from models import db, User, Event, EventMember
from models import EventStatus, JoinStatus, EventType

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///event_planner.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'secret-key-123'
app.config['JSON_AS_ASCII'] = False

db.init_app(app)

with app.app_context():
    db.create_all()
    print("База данных готова")

# ========== СТРАНИЦЫ ==========

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/event/<int:event_id>')
def event_page(event_id):
    return render_template('event.html', event_id=event_id)

# ========== API ==========

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json
    
    if User.query.filter_by(phone=data['phone']).first():
        return jsonify({'error': 'Телефон уже зарегистрирован'}), 400
    
    user = User(
        phone=data['phone'],
        password_hash=generate_password_hash(data['password']),
        name=data['name'],
        surname=data['surname']
    )
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        'user_id': user.user_id,
        'name': user.name,
        'surname': user.surname
    })

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    user = User.query.filter_by(phone=data['phone']).first()
    
    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'error': 'Неверный телефон или пароль'}), 401
    
    return jsonify({
        'user_id': user.user_id,
        'name': user.name,
        'surname': user.surname
    })

@app.route('/api/events', methods=['POST'])
def api_create_event():
    data = request.json
    
    event = Event(
        title=data['title'],
        creator_id=data['creator_id'],
        event_type=EventType.OTHER,
        status=EventStatus.PUBLISHED
    )
    db.session.add(event)
    db.session.flush()
    
    # Добавляем создателя как участника
    existing = EventMember.query.filter_by(event_id=event.event_id, user_id=data['creator_id']).first()
    if not existing:
        member = EventMember(
            event_id=event.event_id,
            user_id=data['creator_id'],
            join_status=JoinStatus.ACCEPTED,
            invite_token='token_' + str(event.event_id)
        )
        db.session.add(member)
    
    db.session.commit()
    
    return jsonify({
        'event_id': event.event_id,
        'title': event.title
    })

@app.route('/api/events/user/<int:user_id>', methods=['GET'])
def api_user_events(user_id):
    events = db.session.query(Event).join(EventMember).filter(EventMember.user_id == user_id).all()
    
    result = []
    for event in events:
        result.append({
            'event_id': event.event_id,
            'title': event.title
        })
    
    return jsonify(result)

@app.route('/api/events/<int:event_id>', methods=['GET'])
def api_get_event(event_id):
    event = Event.query.get_or_404(event_id)
    
    return jsonify({
        'event_id': event.event_id,
        'title': event.title,
        'creator_id': event.creator_id
    })

# ========== API УЧАСТНИКИ ==========

@app.route('/api/events/<int:event_id>/add-member', methods=['POST'])
def api_add_member(event_id):
    """Добавление участника по ID"""
    data = request.json
    user_id = data['user_id']
    invited_user_id = data['invited_user_id']
    
    # Проверяем, что приглашающий - участник мероприятия
    is_member = EventMember.query.filter_by(event_id=event_id, user_id=user_id).first()
    if not is_member:
        return jsonify({'error': 'Вы не участник мероприятия'}), 403
    
    # Проверяем, не добавлен ли уже пользователь
    existing = EventMember.query.filter_by(event_id=event_id, user_id=invited_user_id).first()
    if existing:
        return jsonify({'error': 'Пользователь уже в мероприятии'}), 400
    
    # Добавляем участника
    member = EventMember(
        event_id=event_id,
        user_id=invited_user_id,
        join_status=JoinStatus.ACCEPTED,
        invite_token='token_' + str(event_id) + '_' + str(invited_user_id)
    )
    db.session.add(member)
    db.session.commit()
    
    return jsonify({'message': 'Участник добавлен'})

@app.route('/api/events/<int:event_id>/members', methods=['GET'])
def api_get_members(event_id):
    """Получение списка участников"""
    members = db.session.query(EventMember, User).join(User, EventMember.user_id == User.user_id).filter(
        EventMember.event_id == event_id
    ).all()
    
    result = []
    for member, user in members:
        result.append({
            'user_id': user.user_id,
            'name': user.name,
            'surname': user.surname,
            'status': member.join_status.value
        })
    
    return jsonify(result)

@app.route('/api/users/search', methods=['GET'])
def api_search_users():
    """Поиск пользователей по телефону"""
    phone = request.args.get('phone', '')
    current_user_id = request.args.get('current_user_id', type=int)
    
    query = User.query.filter(User.phone.contains(phone))
    if current_user_id:
        query = query.filter(User.user_id != current_user_id)
    
    users = query.limit(5).all()
    
    result = []
    for user in users:
        result.append({
            'user_id': user.user_id,
            'name': user.name,
            'surname': user.surname,
            'phone': user.phone
        })
    
    return jsonify(result)

# ========== API ЧЕК-ЛИСТ ==========

@app.route('/api/events/<int:event_id>/checklist', methods=['GET'])
def api_get_checklist(event_id):
    """Получение чек-листа мероприятия"""
    from models import ChecklistItem
    items = ChecklistItem.query.filter_by(event_id=event_id).all()
    
    result = []
    for item in items:
        result.append({
            'item_id': item.item_id,
            'text': item.text,
            'is_completed': item.is_completed
        })
    
    return jsonify(result)

@app.route('/api/checklist', methods=['POST'])
def api_add_checklist_item():
    """Добавление пункта в чек-лист"""
    from models import ChecklistItem
    data = request.json
    
    item = ChecklistItem(
        event_id=data['event_id'],
        text=data['text'],
        is_completed=False
    )
    db.session.add(item)
    db.session.commit()
    
    return jsonify({
        'message': 'Пункт добавлен',
        'item_id': item.item_id
    })

@app.route('/api/checklist/<int:item_id>', methods=['PUT'])
def api_toggle_checklist_item(item_id):
    """Переключение статуса пункта (выполнено/не выполнено)"""
    from models import ChecklistItem
    item = ChecklistItem.query.get_or_404(item_id)
    item.is_completed = not item.is_completed
    db.session.commit()
    
    return jsonify({
        'message': 'Статус обновлен',
        'is_completed': item.is_completed
    })

@app.route('/api/checklist/<int:item_id>', methods=['DELETE'])
def api_delete_checklist_item(item_id):
    """Удаление пункта из чек-листа"""
    from models import ChecklistItem
    item = ChecklistItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    
    return jsonify({'message': 'Пункт удален'})

@app.route('/api/checklist/<int:item_id>', methods=['PATCH'])
def api_update_checklist_text(item_id):
    """Обновление текста пункта"""
    from models import ChecklistItem
    data = request.json
    item = ChecklistItem.query.get_or_404(item_id)
    item.text = data['text']
    db.session.commit()
    
    return jsonify({'message': 'Текст обновлен'})

# ========== API СЛОТЫ И ГОЛОСОВАНИЕ ==========

@app.route('/api/events/<int:event_id>/slots', methods=['GET'])
def api_get_slots(event_id):
    """Получение всех слотов мероприятия с количеством голосов"""
    from models import EventSlot, Vote
    slots = EventSlot.query.filter_by(event_id=event_id).all()
    
    result = []
    for slot in slots:
        # Считаем количество голосов за этот слот
        votes_count = Vote.query.filter_by(slot_id=slot.slot_id).count()
        
        # Проверяем, голосовал ли текущий пользователь за этот слот
        user_id = request.args.get('user_id', type=int)
        user_voted = False
        if user_id:
            user_vote = Vote.query.filter_by(slot_id=slot.slot_id, user_id=user_id).first()
            user_voted = user_vote is not None
        
        result.append({
            'slot_id': slot.slot_id,
            'time': slot.time.isoformat(),
            'place_name': slot.place_name,
            'place_address': slot.place_address,
            'created_by': slot.created_by,
            'votes_count': votes_count,
            'user_voted': user_voted
        })
    
    return jsonify(result)

@app.route('/api/events/<int:event_id>/slots', methods=['POST'])
def api_add_slot(event_id):
    """Добавление нового слота (варианта времени и места)"""
    from models import EventSlot
    data = request.json
    
    slot = EventSlot(
        event_id=event_id,
        time=datetime.fromisoformat(data['time']),
        place_name=data['place_name'],
        place_address=data['place_address'],
        created_by=data['created_by'],
        date=datetime.fromisoformat(data['time']).date()
    )
    db.session.add(slot)
    db.session.commit()
    
    return jsonify({'slot_id': slot.slot_id, 'message': 'Вариант добавлен'})

@app.route('/api/votes', methods=['POST'])
def api_vote():
    """Голосование за слот (только один голос на пользователя)"""
    from models import Vote
    data = request.json
    
    user_id = data['user_id']
    event_id = data['event_id']
    slot_id = data['slot_id']
    
    # Удаляем все предыдущие голоса пользователя за это мероприятие
    Vote.query.filter_by(user_id=user_id, event_id=event_id).delete()
    
    # Добавляем новый голос
    vote = Vote(
        slot_id=slot_id,
        user_id=user_id,
        event_id=event_id,
        preference=1  # Значение не важно, просто отметка
    )
    db.session.add(vote)
    db.session.commit()
    
    return jsonify({'message': 'Голос учтен'})

@app.route('/api/events/<int:event_id>/finalize-slot', methods=['POST'])
def api_finalize_slot(event_id):
    """Выбор финального слота (только для создателя)"""
    data = request.json
    event = Event.query.get_or_404(event_id)
    
    if event.creator_id != data['user_id']:
        return jsonify({'error': 'Только создатель может выбрать финальный вариант'}), 403
    
    event.final_slot_id = data['slot_id']
    db.session.commit()
    
    return jsonify({'message': 'Финальный вариант выбран'})

@app.route('/api/events/<int:event_id>/my-vote', methods=['GET'])
def api_get_my_vote(event_id):
    """Получение голоса текущего пользователя"""
    from models import Vote
    user_id = request.args.get('user_id', type=int)
    
    if user_id:
        vote = Vote.query.filter_by(event_id=event_id, user_id=user_id).first()
        if vote:
            return jsonify({'slot_id': vote.slot_id})
    
    return jsonify({'slot_id': None})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)