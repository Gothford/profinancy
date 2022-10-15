from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import configuration as cfg
import redis

app = FastAPI()
rd = redis.Redis(host=cfg.REDIS_HOST, port=cfg.REDIS_PORT, decode_responses=True)


class VoteCreator(BaseModel):
    vote_name: str
    vote_answers: list


class Vote(BaseModel):
    vote_id: int
    vote_answer: str


@app.get("/")
async def root():
    return "this is gothford`s solution of test task by profinancy"


@app.on_event('shutdown')
async def shutdown():
    rd.flushdb()
    rd.close()
    print("server is shutdown and db is flushed")


@app.get("/get_results/{vote_id}")
async def results(vote_id: int):
    # вернуть результаты голосования в процентах
    current_vote = rd.hgetall(vote_id)
    if current_vote:
        vote_results = dict(list(current_vote.items())[1:])
        sum_of_votes = sum(int(res) for res in vote_results.values())
        response_data = dict(vote_id=vote_id,
                             vote_name=current_vote["vote_name"])
        for vote_option, vote_result in vote_results.items():
            percent_of_vote = (int(vote_result)/sum_of_votes)*100
            buffer_data = {vote_option: percent_of_vote}
            response_data.update(buffer_data)
        return response_data
    else:
        return HTTPException(status_code=400, detail="vote is not found")


@app.post("/create_vote")
async def create_vote(data: VoteCreator):
    """
    сохранить в редис новое голосование
    подразумевается, что запрос будет приходить в формате:
    {
    "vote_name": "vote1",
    "vote_answers": [
        "var1",
        "var2"]
    }
    так как в описании задания не было примеров запроса, надеюсь, вы будете придерживаться моей модели
    возвращает json в формате {"vote_id": int(datetime.now().timestamp() * 1000)}

    p.s. с редисом разбирался на лету (как и с fastapi, т.к. хотелось подтянуть знания),
         видел, что hmset уже deprecated но, в целях экономии времени,
         решил пользоваться именно им, основной "посыл" моего решения заключается в том,
         что я могу разобраться с тем, чего не знаю, но мне это нужно для текущей задачи,
         а уже "отшлифовать шероховатости" могу после code review и советов старших коллег
    """

    data = dict(data)
    vote_id = int(datetime.now().timestamp() * 1000)
    current_vote = {"vote_name": data["vote_name"]}
    current_vote.update({i: 0 for i in data["vote_answers"]})
    rd.hmset(vote_id, {i: j for i, j in current_vote.items()})
    return {"vote_id": vote_id}


@app.post("/vote")
async def vote(data: Vote):
    """
    проголосовать
    подразумевается, что запрос будет приходить в формате:
    {
    "vote_id": int,
    "vote_answer": str (вариант ответа строкой)
    }
    так как в описании задания не было примеров запроса, надеюсь, вы будете придерживаться моей модели
    """
    data = dict(data)

    if rd.hgetall(data["vote_id"]):
        rd.hincrby(data["vote_id"], data["vote_answer"], 1)
    else:
        return HTTPException(status_code=400, detail="vote is not found")
    return "your vote has been counted"

if __name__ == '__main__':
    uvicorn.run("main:app", host=cfg.APP_HOST, port=cfg.APP_PORT, reload=cfg.IS_DEBUG)
