import customtkinter as ctk
import threading
import logging
from binance import Client
from binance.exceptions import BinanceAPIException
import time
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class BasicBot:
    def __init__(self, api_key=None, api_secret=None, mock=True):
        self.mock = mock or not (api_key and api_secret)
        self.client = Client(api_key or '', api_secret or '')
        self.client.FUTURES_URL = 'https://testnet.binancefuture.com'

        logging.info(f"BasicBot initialized (mock={self.mock})")

    def get_market_price(self, symbol):
            try:
                resp = requests.get(
                    "https://testnet.binancefuture.com/fapi/v1/ticker/price",
                    params={"symbol": symbol},
                    timeout=5
                )
                resp.raise_for_status()
                data = resp.json()
                price = float(data["price"])
                logging.info(f"Public fetch price {price} for {symbol}")
                return price
            except Exception as e:
                logging.error(f"Error fetching public price: {e}")
                return 0.0

    def get_balance(self):
        try:
            bal = self.client.futures_account_balance()
            for entry in bal:
                if entry['asset'] == 'USDT':
                    return float(entry['balance'])
            return 0.0
        except Exception as e:
            logging.error(f"Error fetching balance: {e}")
            return 0.0

    def place_order(self, symbol, side, order_type, quantity, price, leverage, stop_loss):
        params = {
            'symbol': symbol,
            'side': side,
            'type': order_type.upper(),
            'quantity': quantity,
        }
        if order_type == 'limit':
            params.update({'price': price, 'timeInForce': 'GTC'})
        try:
            if not self.mock:
                self.client.futures_change_leverage(symbol=symbol, leverage=int(leverage))
                order = self.client.futures_create_order(**params)
                logging.info(f"Order placed: {order}")
                if stop_loss:
                    sl_price = float(stop_loss)
                    sl_side = 'SELL' if side=='BUY' else 'BUY'
                    self.client.futures_create_order(
                        symbol=symbol,
                        side=sl_side,
                        type='STOP_MARKET',
                        stopPrice=sl_price,
                        closePosition=True
                    )
                return order
            else:
                logging.info(f"Mock order: {params}, leverage={leverage}, stop_loss={stop_loss}")
                return {'mock': True, **params}
        except BinanceAPIException as e:
            logging.error(f"Binance API error: {e.message}")
            return None
        except Exception as e:
            logging.error(f"Error placing order: {e}")
            return None

class GUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Trading Bot")
        self.geometry("800x600")

        self.api_key = ctk.StringVar()
        self.api_secret = ctk.StringVar()
        self.mock_mode = ctk.BooleanVar(value=True)
        self.symbol = ctk.StringVar(value="BTCUSDT")
        self.market_price = ctk.StringVar(value="0.0")
        self.balance = ctk.StringVar(value="0.0 USDT")
        self.order_type = ctk.StringVar(value="market")
        self.side = ctk.StringVar(value="BUY")
        self.quantity = ctk.StringVar()
        self.price = ctk.StringVar()
        self.leverage = ctk.StringVar()
        self.stop_loss = ctk.StringVar()
        self.auto_trade = ctk.BooleanVar(value=False)

        self.bot = BasicBot(mock=True)

        self._create_widgets()
        self._refresh_data()

    def _create_widgets(self):
        pad = 10
        bg_color = "#121212"
        frame_color = "#1E1E1E"
        text_color = "#FFFFFF"
        accent_color = "#F0B90B"
        field_bg = "#333333"

        self.notebook = ctk.CTkTabview(self, fg_color=bg_color)
        self.notebook.pack(fill="both", expand=True, padx=pad, pady=pad)
        trading_tab = self.notebook.add("Trading")
        settings_tab = self.notebook.add("Add API Key")

        top = ctk.CTkFrame(trading_tab, fg_color=frame_color)
        top.pack(fill="x", padx=pad, pady=pad)
        for i in range(3):
            top.grid_columnconfigure(i, weight=1)

        f1 = ctk.CTkFrame(top, fg_color=frame_color)
        f1.grid(row=0, column=0, sticky="ew", padx=pad)

        ctk.CTkLabel(f1, text="Symbol:", text_color=text_color).pack(side="left")

        self.symbol_dropdown = ctk.CTkOptionMenu(
            f1,
            values=["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT", "Custom"],
            variable=self.symbol,
            fg_color=accent_color,
            button_color="#8B7500",
            dropdown_text_color="white",
            text_color="black",
            command=self._on_symbol_change
        )
        self.symbol_dropdown.pack(side="left", padx=5)

        self.custom_symbol_entry = ctk.CTkEntry(
            f1,
            textvariable=self.symbol,
            placeholder_text="Enter symbol",
            fg_color=field_bg,
            text_color=text_color
        )
        self.custom_symbol_entry.pack_forget()

        f2 = ctk.CTkFrame(top, fg_color=frame_color)
        f2.grid(row=0, column=1, sticky="ew", padx=pad)
        ctk.CTkLabel(f2, text="Price:", text_color=text_color).pack(side="left")
        ctk.CTkLabel(
            f2,
            textvariable=self.market_price,
            text_color=accent_color,
            font=(None, 16, "bold")
        ).pack(side="left", padx=5)

        f3 = ctk.CTkFrame(top, fg_color=frame_color)
        f3.grid(row=0, column=2, sticky="ew", padx=pad)
        ctk.CTkLabel(f3, text="Balance:", text_color=text_color).pack(side="left")
        ctk.CTkLabel(
            f3,
            textvariable=self.balance,
            text_color=accent_color,
            font=(None, 14)
        ).pack(side="left", padx=5)

        of = ctk.CTkFrame(trading_tab, fg_color=frame_color)
        of.pack(fill="x", padx=pad, pady=(0, pad))
        
        tframe = ctk.CTkFrame(of, fg_color=frame_color)
        tframe.pack(fill="x", pady=5)
        ctk.CTkLabel(tframe, text="Order Type:", text_color=text_color).pack(side="left", padx=pad)
        for v in ("market", "limit"):
            ctk.CTkRadioButton(
                tframe,
                text=v.title(),
                variable=self.order_type,
                value=v,
                fg_color=accent_color,
                text_color=text_color,
                command=self._update_order_form
            ).pack(side="left", padx=pad)

        sframe = ctk.CTkFrame(of, fg_color=frame_color)
        sframe.pack(fill="x", pady=5)
        ctk.CTkLabel(sframe, text="Side:", text_color=text_color).pack(side="left", padx=pad)
        ctk.CTkRadioButton(
            sframe,
            text="Buy",
            variable=self.side,
            value="BUY",
            fg_color="#00C853",
            text_color=text_color
        ).pack(side="left", padx=pad)
        ctk.CTkRadioButton(
            sframe,
            text="Sell",
            variable=self.side,
            value="SELL",
            fg_color="#F44336",
            text_color=text_color
        ).pack(side="left", padx=pad)

        qf = ctk.CTkFrame(of, fg_color=frame_color)
        qf.pack(fill="x", pady=5)
        ctk.CTkLabel(qf, text="Quantity:", text_color=text_color).pack(side="left", padx=pad)
        ctk.CTkEntry(
            qf,
            textvariable=self.quantity,
            fg_color=field_bg,
            text_color=text_color,
            placeholder_text="0.001"
        ).pack(side="left", padx=pad, fill="x", expand=True)

        self.pf = ctk.CTkFrame(of, fg_color=frame_color)
        ctk.CTkLabel(self.pf, text="Price:", text_color=text_color).pack(side="left", padx=pad)
        ctk.CTkEntry(
            self.pf,
            textvariable=self.price,
            fg_color=field_bg,
            text_color=text_color,
            placeholder_text="Limit price"
        ).pack(side="left", padx=pad, fill="x", expand=True)

        lf = ctk.CTkFrame(of, fg_color=frame_color)
        lf.pack(fill="x", pady=5)
        ctk.CTkLabel(lf, text="Leverage:", text_color=text_color).pack(side="left", padx=pad)
        ctk.CTkEntry(
            lf,
            textvariable=self.leverage,
            fg_color=field_bg,
            text_color=text_color,
            placeholder_text="10"
        ).pack(side="left", padx=pad, fill="x", expand=True)

        slf = ctk.CTkFrame(of, fg_color=frame_color)
        slf.pack(fill="x", pady=5)
        ctk.CTkLabel(slf, text="Stop‑Loss:", text_color=text_color).pack(side="left", padx=pad)
        ctk.CTkEntry(
            slf,
            textvariable=self.stop_loss,
            fg_color=field_bg,
            text_color=text_color,
            placeholder_text="Price"
        ).pack(side="left", padx=pad, fill="x", expand=True)

        bf = ctk.CTkFrame(of, fg_color=frame_color)
        bf.pack(fill="x", pady=10)
        ctk.CTkButton(
            bf,
            text="Place Order",
            command=self._place_order,
            fg_color=accent_color,
            text_color="black"
        ).pack(side="left", padx=pad, expand=True, fill="x")
        ctk.CTkButton(
            bf,
            text="Refresh",
            command=self._refresh_data,
            fg_color="#444444",
            text_color="white"
        ).pack(side="left", padx=pad, expand=True, fill="x")

        af = ctk.CTkFrame(of, fg_color=frame_color)
        af.pack(fill="x", pady=5)
        ctk.CTkLabel(af, text="Auto Trading:", text_color=text_color).pack(side="left", padx=pad)
        ctk.CTkSwitch(
            af,
            variable=self.auto_trade,
            fg_color="#444444",
            progress_color=accent_color,
            button_color="#FFFFFF",
            button_hover_color="#F5F5F5",
            text_color=text_color,
            command=self._toggle_auto_trade
        ).pack(side="left", padx=pad)

        lf = ctk.CTkFrame(trading_tab, fg_color=frame_color)
        lf.pack(fill="both", expand=True, padx=pad, pady=pad)
        ctk.CTkLabel(lf, text="Activity Log", text_color=text_color).pack(pady=(0, pad))
        self.log_text = ctk.CTkTextbox(lf, fg_color=field_bg, text_color=text_color, font=("Consolas", 12))
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")

        sf = ctk.CTkFrame(settings_tab, fg_color=frame_color)
        sf.pack(fill="both", expand=True, padx=pad, pady=pad)
        
        for lbl, var, hide in [
            ("API Key:",    self.api_key,    False),
            ("API Secret:", self.api_secret, True)
        ]:
            fx = ctk.CTkFrame(sf, fg_color=frame_color)
            fx.pack(fill="x", pady=5)
            ctk.CTkLabel(fx, text=lbl, text_color=text_color).pack(side="left", padx=pad)
            ctk.CTkEntry(
                fx,
                textvariable=var,
                show="*" if hide else "",
                fg_color=field_bg,
                text_color=text_color,
                placeholder_text=lbl
            ).pack(side="left", padx=pad, fill="x", expand=True)
        ctk.CTkButton(
            sf,
            text="Apply Settings",
            command=self._apply_settings,
            fg_color=accent_color,
            text_color="black"
        ).pack(pady=20)

    def _update_order_form(self):
        if self.order_type.get() == 'limit':
            self.pf.pack(fill="x", pady=5)
        else:
            self.pf.pack_forget()

    def _on_symbol_change(self, selected=None):
        if self.symbol.get() == "Custom":
            self.custom_symbol_entry.pack(side="left", padx=2)
            return
        else:
            self.custom_symbol_entry.pack_forget()

        symbol = self.symbol.get()
        price = self.bot.get_market_price(symbol)
        self.market_price.set(f"{price:.4f}")
        bal = self.bot.get_balance()
        self.balance.set(f"{bal:.2f} USDT")
        self._log(f"Symbol changed to {symbol} | Price: {price} | Balance: {bal}")

    def _refresh_data(self):
        sym = self.symbol.get()
        if sym == "Custom":
            sym = self.custom_symbol_entry.get().upper()
            self.symbol.set(sym)
        self._on_symbol_change()

    def _place_order(self):
        params = {
            'symbol': self.symbol.get(),
            'side': self.side.get(),
            'order_type': self.order_type.get(),
            'quantity': float(self.quantity.get()),
            'price': float(self.price.get()) if self.price.get() else None,
            'leverage': int(self.leverage.get()) if self.leverage.get() else 1,
            'stop_loss': float(self.stop_loss.get()) if self.stop_loss.get() else None
        }
        self._log(f"Placing order: {params}")
        result = self.bot.place_order(**params)
        self._log(f"Order result: {result}")

    def _toggle_auto_trade(self):
        if self.auto_trade.get():
            self._log("Auto-trading enabled.")
            t = threading.Thread(target=self._auto_trade_loop, daemon=True)
            t.start()
        else:
            self._log("Auto-trading disabled.")

    def _auto_trade_loop(self):
        while self.auto_trade.get():
            self._place_order()
            time.sleep(60)

    def _apply_settings(self):
        mock = self.mock_mode.get() or not (self.api_key.get() and self.api_secret.get())
        self.bot = BasicBot(api_key=self.api_key.get(), api_secret=self.api_secret.get(), mock=mock)
        self._log(f"Settings applied. mock={mock}")

    def _log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{message}\n")
        self.log_text.configure(state="disabled")

if __name__ == '__main__':
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = GUI()
    app.mainloop()