from app import app, db, User, Survey, Question, Option, Response, Answer
from werkzeug.security import generate_password_hash


with app.app_context():
    user = User.query.filter_by(username='demo').first()
    if not user:
        user = User(username='demo')
        db.session.add(user)
    user.password_hash = generate_password_hash('demo123456')
    db.session.flush()

    title = '校园最受欢迎活动投票（示例）'
    survey = Survey.query.filter_by(title=title, user_id=user.id).first()
    if survey:
        print('示例问卷已经存在，本次只重置 demo 密码。')
    else:
        survey = Survey(
            title=title,
            description='请选择你最喜欢的校园活动，每人只能提交一次。',
            user_id=user.id,
        )
        db.session.add(survey)
        db.session.flush()

        questions = [
            ('你最喜欢哪类校园活动？', 'single', ['文艺晚会', '体育比赛', '社团活动', '学术讲座', '志愿服务']),
            ('你通常参加校园活动的频率是？', 'single', ['每周参加', '每月参加', '偶尔参加', '几乎不参加']),
            ('你希望学校增加哪些活动？', 'multiple', ['音乐类活动', '体育类活动', '创新创业活动', '游戏娱乐活动', '志愿服务活动']),
            ('你认为校园活动最需要改进哪些方面？', 'multiple', ['活动宣传', '活动时间', '活动场地', '奖品设置', '组织流程']),
            ('你最希望学校举办的具体活动是什么？', 'text', []),
        ]
        created_questions = []
        for position, (text, kind, option_texts) in enumerate(questions):
            question = Question(survey_id=survey.id, text=text, kind=kind, required=(position < 4), position=position)
            db.session.add(question)
            db.session.flush()
            created_questions.append(question)
            for option_position, option_text in enumerate(option_texts):
                db.session.add(Option(question_id=question.id, text=option_text, position=option_position))
        db.session.commit()

        options = {q.id: Option.query.filter_by(question_id=q.id).order_by(Option.position).all() for q in created_questions}
        for index in range(12):
            response = Response(
                survey_id=survey.id,
                ip_hash=f'seed-ip-{index}',
                visitor_token=f'seed-token-{index}',
            )
            db.session.add(response)
            db.session.flush()

            first = options[created_questions[0].id][index % 5]
            second = options[created_questions[1].id][index % 4]
            multi_one = options[created_questions[2].id][index % 5]
            multi_two = options[created_questions[2].id][(index + 2) % 5]
            improve_one = options[created_questions[3].id][index % 5]
            improve_two = options[created_questions[3].id][(index + 1) % 5]
            db.session.add_all([
                Answer(response_id=response.id, question_id=created_questions[0].id, option_id=first.id),
                Answer(response_id=response.id, question_id=created_questions[1].id, option_id=second.id),
                Answer(response_id=response.id, question_id=created_questions[2].id, option_id=multi_one.id),
                Answer(response_id=response.id, question_id=created_questions[2].id, option_id=multi_two.id),
                Answer(response_id=response.id, question_id=created_questions[3].id, option_id=improve_one.id),
                Answer(response_id=response.id, question_id=created_questions[3].id, option_id=improve_two.id),
                Answer(response_id=response.id, question_id=created_questions[4].id, text_value=f'希望增加第 {index + 1} 位同学喜欢的校园活动'),
            ])
        db.session.commit()
        print('已创建示例问卷，并生成 12 条答卷。')

    print('测试账号：demo / demo123456')
