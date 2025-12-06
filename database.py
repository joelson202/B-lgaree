import json
import os
import traceback
from supabase import create_client, Client

class DatabaseManager:
    def __init__(self, local_file="products.json"):
        self.local_file = local_file
        self.supabase: Client = None
        # Default config (Public Anon Key)
        self.url = "https://nkfvlunepuyutbmfwxby.supabase.co"
        self.key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5rZnZsdW5lcHV5dXRibWZ3eGJ5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUwNDE1NDAsImV4cCI6MjA4MDYxNzU0MH0.Gn70bCuUFENhTS_hmj-5DLD857UHQwDCi9Vc0bDadNY"
        self.config_file = "config.json"
        self.user = None
        self.load_config()
        if self.url and self.key:
             self.init_supabase()

    def load_config(self):
        """Carrega configurações de conexão (URL, KEY) se existirem e forem diferentes do padrão."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    url = config.get("supabase_url", "")
                    key = config.get("supabase_key", "")
                    if url and key:
                        self.url = url
                        self.key = key
            except Exception as e:
                print(f"Erro ao carregar config: {e}")

    def save_config(self, url, key):
        self.url = url
        self.key = key
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump({"supabase_url": url, "supabase_key": key}, f)
            if self.url and self.key:
                return self.init_supabase()
        except Exception as e:
            print(f"Erro ao salvar config: {e}")
            return False
        return True

    def init_supabase(self):
        try:
            self.supabase = create_client(self.url, self.key)
            return True
        except Exception as e:
            print(f"Erro ao iniciar Supabase: {e}")
            return False

    def login(self, email, password):
        if not self.supabase:
            if not self.init_supabase():
                return False, "Erro ao conectar ao servidor."
        try:
            response = self.supabase.auth.sign_in_with_password({"email": email, "password": password})
            self.user = response.user
            return True, "Login realizado com sucesso."
        except Exception as e:
            return False, f"Erro no login: {str(e)}"

    def register(self, email, password):
        if not self.supabase:
            if not self.init_supabase():
                return False, "Erro ao conectar ao servidor."
        try:
            response = self.supabase.auth.sign_up({"email": email, "password": password})
            # Verifica se user foi criado
            if response.user:
                 self.user = response.user
                 return True, "Cadastro realizado! Faça login."
            return True, "Cadastro enviado. Verifique seu email."
        except Exception as e:
            return False, f"Erro no cadastro: {str(e)}"

    def get_current_user_id(self):
        if self.user:
            return self.user.id
        if self.supabase:
            session = self.supabase.auth.get_session()
            if session and session.user:
                self.user = session.user
                return self.user.id
        return None

    def save_local(self, data):
        """Salva dados localmente em JSON."""
        try:
            with open(self.local_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"Erro ao salvar localmente: {e}")
            return False

    def load_local(self):
        """Carrega dados locais do JSON."""
        if not os.path.exists(self.local_file):
            return []
        try:
            with open(self.local_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Erro ao carregar localmente: {e}")
            return []

    def sync_to_supabase(self, data):
        """Envia dados para o Supabase (upsert)."""
        if not self.supabase:
            # Tentar reconectar se tiver config
            if self.url and self.key:
                if not self.init_supabase():
                    return False, "Falha ao conectar com Supabase."
            else:
                return False, "Supabase não configurado."
        
        user_id = self.get_current_user_id()
        if not user_id:
             return False, "Usuário não autenticado. Faça login."

        try:
            if not data:
                return True, "Nenhum dado para sincronizar."

            # Prepara dados com user_id
            data_to_send = []
            for item in data:
                new_item = item.copy()
                new_item['user_id'] = user_id
                data_to_send.append(new_item)

            # Supabase upsert
            response = self.supabase.table("produtos").upsert(data_to_send).execute()
            return True, "Sincronizado com sucesso."
            
        except Exception as e:
            return False, f"Erro ao sincronizar: {e}"

    def load_from_supabase(self):
        if not self.supabase:
             if self.url and self.key:
                if not self.init_supabase():
                    return None
             else:
                return None

        try:
            response = self.supabase.table("produtos").select("*").execute()
            return response.data
        except Exception as e:
            print(f"Erro ao baixar do Supabase: {e}")
            return None
