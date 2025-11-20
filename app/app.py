import os
from venv import logger
import httpx
from fastapi import FastAPI, Request, HTTPException , APIRouter, Depends
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager

from db import init_engine_and_sessionmaker, get_engine, dispose_engine, Base, get_session
from models import User, FxRate
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession

class App():
    def __init__(self):
        self.BOT_TOKEN = os.environ["BOT_TOKEN"]        
        self.TG_SECRET = os.environ.get("TG_SECRET", "")  
        self.CUR_TOKEN = os.environ["CUR_TOKEN"]
        self.API = f"https://api.telegram.org/bot{self.BOT_TOKEN}"
        self.ADMIN_ID = os.environ.get("ADMIN_ID", "0")
        self.app = FastAPI()

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            init_engine_and_sessionmaker(echo=False)
            engine = get_engine()
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            yield
            await dispose_engine()

        self.app = FastAPI(lifespan=lifespan)

        r = APIRouter()
        r.post("/webhook/{secret}")(self.webhook)
        r.get("/healthz")(self.healthz)
        r.get("/cron")(self.cron_job)
        self.app.include_router(r)

    
    # async def on_startup(self):
    #     init_engine_and_sessionmaker(echo=False)
    #     engine = get_engine()
    #     async with engine.begin() as conn:
    #         await conn.run_sync(Base.metadata.create_all)

    # async def on_shutdown(self):
    #     await dispose_engine()

    async def webhook(self, secret: str, request: Request , session: AsyncSession = Depends(get_session)):
        
        if self.TG_SECRET and secret != self.TG_SECRET:
            raise HTTPException(status_code=403, detail="forbidden")

        update = await request.json()
        msg = update.get("message") or {}
        chat_id = (msg.get("chat") or {}).get("id")
        text = msg.get("text") or ""
        username = (msg.get("from") or {}).get("username", "")
        first = (msg.get("from") or {}).get("first_name", "")
        last = (msg.get("from") or {}).get("last_name", "")
        
        if not chat_id or not text:
            return {"ok": True}
        
        if text.startswith("/start"):

            res = await session.execute(select(User).where(User.tg_id == chat_id))
            if res.scalar_one_or_none() is None:
                await session.execute(
                    insert(User).values(tg_id=chat_id, username=username, first_name=first, last_name=last)
                )
            await session.commit()

            await self.start_message(chat_id)


        elif text == "📊 Exchange Rate": 
            ex_message = await self.ex_rate()
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(f"{self.API}/sendMessage",
                                json={"chat_id": chat_id, "text": ex_message["message"]})

        return {"ok": True}

    async def healthz(self):
        return {"status": "ok"}
    

    async def start_message(self, chat_id: int):
        buttons = {
                "keyboard": [
                    [{"text": "📊 Exchange Rate"},],
                ],
                "resize_keyboard": True
            }

        welcome_message = "👋 Welcome to the Kazakhstan Currency Exchange Bot! 🇰🇿\n\n" \
            "I can provide you with the latest exchange rates for the Kazakhstani Tenge (KZT)" \
            "against major currencies like USD, EUR, and RUB. 💱\n\n"            
        
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(f"{self.API}/sendMessage",
                            json={"chat_id": chat_id, "text": welcome_message, "reply_markup": buttons})
            

    async def ex_rate(self) -> dict:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"https://v6.exchangerate-api.com/v6/{self.CUR_TOKEN}/latest/KZT")
            btc_resp = await client.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd")
            data = resp.json()

            utc5= timezone(timedelta(hours=5))
            date = datetime.fromtimestamp(data.get("time_last_update_unix"),utc5)
            usd_rate = 1 / data["conversion_rates"].get("USD")
            eur_rate = 1 / data["conversion_rates"].get("EUR")
            rub_rate = 1 / data["conversion_rates"].get("RUB")

            message = f"Today's exchange rates ({date}) :\n" \
                    f"🇺🇸 1 USD = {usd_rate:.2f} KZT 🇰🇿\n" \
                    f"🇪🇺 1 EUR = {eur_rate:.2f} KZT 🇰🇿\n" \
                    f"🇷🇺 1 RUB = {rub_rate:.2f} KZT 🇰🇿\n\n" \
                    f"₿ 1 BTC = {btc_resp.json().get('bitcoin').get('usd')} USD 🇺🇸"
            
            return {"usd_rate": usd_rate, "eur_rate": eur_rate, "rub_rate": rub_rate, "message": message, "date": str(date)}
    
    async def cron_job(self , session: AsyncSession = Depends(get_session)):
        async with httpx.AsyncClient(timeout=10) as client:
            ex_rate = await self.ex_rate()
            for user in self.ADMIN_ID.split(","):
                try :
                    await client.post(f"{self.API}/sendMessage",
                                json={"chat_id": user, "text": ex_rate["message"]})
                except Exception as e:
                    logger.error(f"Failed to send cron message to {user}: {e}")
            await self.write_fx_rate(ex_rate , session=session)

    async def write_fx_rate(self, ex_rate: dict , session: AsyncSession):
        ex_rate['date'] = datetime.fromisoformat(ex_rate['date'])
        
        async with session.begin():
            session.add_all([
                FxRate(base="KZT", quote="USD", rate=ex_rate['usd_rate'], as_of=ex_rate['date']),
                FxRate(base="KZT", quote="EUR", rate=ex_rate['eur_rate'], as_of=ex_rate['date']),
                FxRate(base="KZT", quote="RUB", rate=ex_rate['rub_rate'], as_of=ex_rate['date'])
            ])
        


app = App().app