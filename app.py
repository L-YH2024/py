import csv
import hashlib
import io
import os
import uuid
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, Response as FlaskResponse, abort, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()
db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    surveys = db.relationship('Survey', backref='owner', cascade='all, delete-orphan')


class Survey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    deadline = db.Column(db.DateTime, nullable=True)
    closed = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    questions = db.relationship('Question', backref='survey', cascade='all, delete-orphan', order_by='Question.position')
    responses = db.relationship('Response', backref='survey', cascade='all, delete-orphan')

    @property
    def expired(self):
        return self.deadline is not None and datetime.utcnow() > self.deadline

    @property
    def available(self):
        return not self.closed and not self.expired


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    survey_id = db.Column(db.Integer, db.ForeignKey('survey.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    kind = db.Column(db.String(20), nullable=False)
    required = db.Column(db.Boolean, default=True, nullable=False)
    position = db.Column(db.Integer, default=0, nullable=False)
    options = db.relationship('Option', backref='question', cascade='all, delete-orphan', order_by='Option.position')


class Option(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    text = db.Column(db.String(200), nullable=False)
    position = db.Column(db.Integer, default=0, nullable=False)


class Response(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    survey_id = db.Column(db.Integer, db.ForeignKey('survey.id'), nullable=False)
    ip_hash = db.Column(db.String(64), nullable=False)
    visitor_token = db.Column(db.String(64), nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    answers = db.relationship('Answer', backref='response', cascade='all, delete-orphan')
    __table_args__ = (db.UniqueConstraint('survey_id', 'visitor_token', name='uq_survey_visitor'),)


class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    response_id = db.Column(db.Integer, db.ForeignKey('response.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    text_value = db.Column(db.Text, nullable=True)
    option_id = db.Column(db.Integer, db.ForeignKey('option.id'), nullable=True)


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'mysql+pymysql://root:password@127.0.0.1:3306/vote_system?charset=utf8mb4')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    @app.cli.command('init-db')
    def init_db():
        db.create_all()
        print('Database initialized.')

    def login_required():
        if 'user_id' not in session:
            flash('请先登录。', 'warning')
            return redirect(url_for('login', next=request.path))
        return None

    def owner_survey(public_id):
        survey = Survey.query.filter_by(public_id=public_id).first_or_404()
        if survey.user_id != session.get('user_id'):
            abort(403)
        return survey

    @app.context_processor
    def globals_for_templates():
        return {'current_user': User.query.get(session['user_id']) if session.get('user_id') else None}

    @app.route('/')
    def index():
        if session.get('user_id'):
            return redirect(url_for('dashboard'))
        return render_template('index.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            if not username or len(password) < 6:
                flash('用户名不能为空，密码至少 6 位。', 'danger')
            elif User.query.filter_by(username=username).first():
                flash('用户名已存在。', 'danger')
            else:
                db.session.add(User(username=username, password_hash=generate_password_hash(password)))
                db.session.commit()
                flash('注册成功，请登录。', 'success')
                return redirect(url_for('login'))
        return render_template('auth.html', mode='register')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            user = User.query.filter_by(username=request.form.get('username', '').strip()).first()
            if user and check_password_hash(user.password_hash, request.form.get('password', '')):
                session['user_id'] = user.id
                return redirect(request.args.get('next') or url_for('dashboard'))
            flash('用户名或密码错误。', 'danger')
        return render_template('auth.html', mode='login')

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('index'))

    @app.route('/dashboard')
    def dashboard():
        login_redirect = login_required()
        if login_redirect: return login_redirect
        surveys = Survey.query.filter_by(user_id=session['user_id']).order_by(Survey.created_at.desc()).all()
        public_surveys = Survey.query.filter_by(closed=False).order_by(Survey.created_at.desc()).all()
        return render_template('dashboard.html', surveys=surveys, public_surveys=public_surveys)

    @app.route('/survey/new', methods=['GET', 'POST'])
    def create_survey():
        login_redirect = login_required()
        if login_redirect: return login_redirect
        if request.method == 'POST':
            survey = Survey(title=request.form.get('title', '').strip(), description=request.form.get('description', '').strip(), user_id=session['user_id'])
            deadline = request.form.get('deadline', '').strip()
            if deadline:
                survey.deadline = datetime.fromisoformat(deadline)
            if not survey.title:
                flash('标题不能为空。', 'danger')
                return render_template('survey_form.html', survey=None)
            db.session.add(survey)
            db.session.flush()
            texts = request.form.getlist('question_text')
            kinds = request.form.getlist('question_kind')
            requireds = request.form.getlist('required_question')
            options = request.form.getlist('question_options')
            for i, text in enumerate(texts):
                if not text.strip(): continue
                q = Question(survey_id=survey.id, text=text.strip(), kind=kinds[i], required=str(i) in requireds, position=i)
                db.session.add(q)
                db.session.flush()
                for j, option_text in enumerate(options[i].split('|') if i < len(options) else []):
                    if option_text.strip(): db.session.add(Option(question_id=q.id, text=option_text.strip(), position=j))
            db.session.commit()
            flash('问卷创建成功。', 'success')
            return redirect(url_for('dashboard'))
        return render_template('survey_form.html', survey=None)

    @app.route('/survey/<public_id>/close', methods=['POST'])
    def close_survey(public_id):
        login_redirect = login_required()
        if login_redirect: return login_redirect
        survey = owner_survey(public_id)
        survey.closed = True
        db.session.commit()
        flash('问卷已关闭。', 'success')
        return redirect(url_for('dashboard'))

    @app.route('/survey/<public_id>/delete', methods=['POST'])
    def delete_survey(public_id):
        login_redirect = login_required()
        if login_redirect: return login_redirect
        survey = owner_survey(public_id)
        db.session.delete(survey)
        db.session.commit()
        flash('问卷已删除。', 'success')
        return redirect(url_for('dashboard'))

    @app.route('/survey/<public_id>/edit', methods=['GET', 'POST'])
    def edit_survey(public_id):
        login_redirect = login_required()
        if login_redirect: return login_redirect
        survey = owner_survey(public_id)
        if not survey.available:
            flash('问卷已关闭或已超过截止时间，不能编辑。', 'warning')
            return redirect(url_for('dashboard'))
        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            if not title:
                flash('标题不能为空。', 'danger')
                return render_template('survey_form.html', survey=survey, editing=True)
            survey.title = title
            survey.description = request.form.get('description', '').strip()
            deadline = request.form.get('deadline', '').strip()
            survey.deadline = datetime.fromisoformat(deadline) if deadline else None
            if survey.responses:
                db.session.commit()
                flash('该问卷已有答卷，本次仅更新标题、说明和截止时间，题目结构保持不变。', 'info')
                return redirect(url_for('dashboard'))
            for old_question in list(survey.questions): db.session.delete(old_question)
            db.session.flush()
            texts = request.form.getlist('question_text')
            kinds = request.form.getlist('question_kind')
            requireds = request.form.getlist('required_question')
            options = request.form.getlist('question_options')
            for i, text in enumerate(texts):
                if not text.strip(): continue
                q = Question(survey_id=survey.id, text=text.strip(), kind=kinds[i], required=str(i) in requireds, position=i)
                db.session.add(q); db.session.flush()
                for j, option_text in enumerate(options[i].split('|') if i < len(options) else []):
                    if option_text.strip(): db.session.add(Option(question_id=q.id, text=option_text.strip(), position=j))
            db.session.commit()
            flash('问卷修改成功。', 'success')
            return redirect(url_for('dashboard'))
        return render_template('survey_form.html', survey=survey, editing=True)

    @app.route('/survey/<public_id>', methods=['GET', 'POST'])
    def fill_survey(public_id):
        survey = Survey.query.filter_by(public_id=public_id).first_or_404()
        cookie_token = request.cookies.get('visitor_token') or uuid.uuid4().hex
        token = f'user:{session["user_id"]}' if session.get('user_id') else f'guest:{cookie_token}'
        ip_hash = hashlib.sha256(request.remote_addr.encode()).hexdigest()
        if request.method == 'POST':
            if not survey.available: return render_template('message.html', title='问卷已结束', message='该问卷已关闭或超过截止时间。'), 410
            if Response.query.filter_by(survey_id=survey.id, visitor_token=token).first():
                return render_template('message.html', title='请勿重复提交', message='同一填写者只能提交一次。'), 409
            response = Response(survey_id=survey.id, ip_hash=ip_hash, visitor_token=token)
            db.session.add(response)
            db.session.flush()
            for question in survey.questions:
                values = request.form.getlist(f'question_{question.id}')
                if question.required and not any(v.strip() for v in values):
                    db.session.rollback()
                    flash(f'请填写：{question.text}', 'danger')
                    return render_template('fill.html', survey=survey)
                for value in values:
                    if question.kind == 'text': db.session.add(Answer(response_id=response.id, question_id=question.id, text_value=value.strip()))
                    else:
                        option = Option.query.filter_by(id=value, question_id=question.id).first()
                        if option: db.session.add(Answer(response_id=response.id, question_id=question.id, option_id=option.id))
            db.session.commit()
            result = render_template('message.html', title='感谢参与', message='你的回答已成功提交。')
            response = Response.query.get(response.id)
            resp = FlaskResponse(result)
            resp.set_cookie('visitor_token', cookie_token, max_age=31536000, httponly=True, samesite='Lax')
            return resp
        return render_template('fill.html', survey=survey)

    @app.route('/survey/<public_id>/results')
    def results(public_id):
        login_redirect = login_required()
        if login_redirect: return login_redirect
        survey = owner_survey(public_id)
        result_data = []
        for q in survey.questions:
            rows = []
            if q.kind != 'text':
                rows = [{'name': o.text, 'value': Answer.query.filter_by(question_id=q.id, option_id=o.id).count()} for o in q.options]
            else:
                rows = [{'text': a.text_value} for a in Answer.query.filter_by(question_id=q.id).all() if a.text_value]
            result_data.append({'id': q.id, 'text': q.text, 'kind': q.kind, 'rows': rows})
        return render_template('results.html', survey=survey, result_data=result_data, response_count=len(survey.responses))

    @app.route('/survey/<public_id>/export.csv')
    def export_csv(public_id):
        login_redirect = login_required()
        if login_redirect: return login_redirect
        survey = owner_survey(public_id)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['题目', '选项/答案', '数量'])
        for q in survey.questions:
            if q.kind == 'text':
                for answer in Answer.query.filter_by(question_id=q.id).all(): writer.writerow([q.text, answer.text_value or '', 1])
            else:
                for option in q.options: writer.writerow([q.text, option.text, Answer.query.filter_by(question_id=q.id, option_id=option.id).count()])
        return FlaskResponse('\ufeff' + output.getvalue(), mimetype='text/csv; charset=utf-8', headers={'Content-Disposition': f'attachment; filename=survey_{survey.id}.csv'})

    with app.app_context():
        db.create_all()
    return app


app = create_app()


if __name__ == '__main__':
    app.run(debug=True)
