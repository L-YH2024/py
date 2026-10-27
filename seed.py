from app import app, db, User, Survey, Question, Option, Response, Answer
from werkzeug.security import generate_password_hash

with app.app_context():
    user = User.query.filter_by(username='demo').first()
    if not user:
        user = User(username='demo')
        db.session.add(user)
    user.password_hash = generate_password_hash('demo123456')
    db.session.flush()
    survey = Survey.query.filter_by(title='课程设计示例问卷').first()
    if not survey:
        survey = Survey(title='课程设计示例问卷', description='用于现场演示的测试问卷', user_id=user.id); db.session.add(survey); db.session.flush()
        q1 = Question(survey_id=survey.id, text='你最喜欢的开发语言？', kind='single', position=0); q2 = Question(survey_id=survey.id, text='你希望增加哪些功能？', kind='multiple', position=1); db.session.add_all([q1,q2]); db.session.flush()
        for q, values in [(q1,['Python','Java','JavaScript']), (q2,['导出报表','权限管理','移动端'])]:
            for i, value in enumerate(values): db.session.add(Option(question_id=q.id, text=value, position=i))
        db.session.commit()
        for i in range(12):
            response = Response(survey_id=survey.id, ip_hash=f'seed-ip-{i}', visitor_token=f'seed-token-{i}'); db.session.add(response); db.session.flush()
            o1 = Option.query.filter_by(question_id=q1.id).all()[i % 3]; db.session.add(Answer(response_id=response.id, question_id=q1.id, option_id=o1.id))
            o2 = Option.query.filter_by(question_id=q2.id).all()[i % 3]; db.session.add(Answer(response_id=response.id, question_id=q2.id, option_id=o2.id))
        db.session.commit()
        print('Seeded demo account and 12 responses.')
