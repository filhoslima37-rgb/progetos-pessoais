import hashlib
import hmac
import re
import secrets
import sqlite3
from contextlib import closing

from database import conectar, criar_tabela


_ITERACOES_HASH = 600_000
_TAMANHO_SALT = 16
_TAMANHO_HASH = 32
_SALT_DUMMY = b"\0" * _TAMANHO_SALT
_HASH_DUMMY = hashlib.pbkdf2_hmac(
    "sha256", b"dummy", _SALT_DUMMY, _ITERACOES_HASH, dklen=_TAMANHO_HASH
).hex()
_SENHA_HASH_DUMMY = (
    f"pbkdf2_sha256${_ITERACOES_HASH}${_SALT_DUMMY.hex()}${_HASH_DUMMY}"
)


def _validar_usuario(nome_usuario, email, senha):
    if not isinstance(nome_usuario, str):
        raise ValueError("Informe um nome de usuário válido.")
    nome_usuario = nome_usuario.strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,30}", nome_usuario):
        raise ValueError(
            "O nome de usuário deve ter de 3 a 30 caracteres: letras, números, ponto, hífen ou underscore."
        )
    if not isinstance(email, str):
        raise ValueError("Informe um e-mail válido.")
    email = email.strip().casefold()
    if len(email) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError("Informe um e-mail válido.")
    if not isinstance(senha, str) or len(senha) < 12:
        raise ValueError("A senha deve ter pelo menos 12 caracteres.")
    return nome_usuario, email


def _criar_hash(senha):
    salt = secrets.token_bytes(_TAMANHO_SALT)
    digest = hashlib.pbkdf2_hmac(
        "sha256", senha.encode("utf-8"), salt, _ITERACOES_HASH, dklen=_TAMANHO_HASH
    )
    return f"pbkdf2_sha256${_ITERACOES_HASH}${salt.hex()}${digest.hex()}"


def _verificar_hash(senha, senha_hash):
    try:
        algoritmo, iteracoes, salt_hex, digest_hex = senha_hash.split("$", 3)
        if algoritmo != "pbkdf2_sha256":
            return False
        iteracoes = int(iteracoes)
        if not 100_000 <= iteracoes <= 2_000_000:
            return False
        salt = bytes.fromhex(salt_hex)
        digest_esperado = bytes.fromhex(digest_hex)
        digest_atual = hashlib.pbkdf2_hmac(
            "sha256", senha.encode("utf-8"), salt, iteracoes,
            dklen=len(digest_esperado),
        )
        return hmac.compare_digest(digest_atual, digest_esperado)
    except (AttributeError, TypeError, ValueError):
        return False


def cadastrar_usuario(nome_usuario, email, senha, caminho=None):
    """Cadastra usuário com hash PBKDF2 e retorna seu ID."""
    nome_usuario, email = _validar_usuario(nome_usuario, email, senha)
    senha_hash = _criar_hash(senha)
    criar_tabela(caminho)

    with closing(conectar(caminho)) as conexao:
        try:
            conexao.execute("BEGIN IMMEDIATE")
            primeiro_usuario = conexao.execute(
                "SELECT 1 FROM usuarios LIMIT 1"
            ).fetchone() is None
            cursor = conexao.execute(
                """INSERT INTO usuarios (nome_usuario, email, senha_hash)
                   VALUES (?, ?, ?)""",
                (nome_usuario, email, senha_hash),
            )
            usuario_id = cursor.lastrowid
            if primeiro_usuario:
                # As transações legadas não tinham dono. Vincula-as somente à
                # primeira conta criada, sem expô-las a cadastros posteriores.
                conexao.execute(
                    "UPDATE transacoes SET usuario_id = ? WHERE usuario_id IS NULL",
                    (usuario_id,),
                )
            conexao.commit()
            return usuario_id
        except sqlite3.IntegrityError as erro:
            conexao.rollback()
            raise ValueError("Nome de usuário ou e-mail já cadastrado.") from erro


def autenticar_usuario(identificador, senha, caminho=None):
    """Aceita nome de usuário ou e-mail; retorna dados públicos ou None."""
    criar_tabela(caminho)
    identificador = identificador.strip() if isinstance(identificador, str) else ""
    with closing(conectar(caminho)) as conexao:
        usuario = conexao.execute(
            """SELECT id, nome_usuario, email, senha_hash
               FROM usuarios
               WHERE nome_usuario = ? COLLATE NOCASE
                  OR email = ? COLLATE NOCASE""",
            (identificador, identificador),
        ).fetchone()

    if usuario is None:
        # Igualar o custo de uma tentativa com usuário inexistente.
        _verificar_hash(senha if isinstance(senha, str) else "", _SENHA_HASH_DUMMY)
        return None
    if not isinstance(senha, str) or not _verificar_hash(senha, usuario["senha_hash"]):
        return None
    return {"id": usuario["id"], "nome_usuario": usuario["nome_usuario"], "email": usuario["email"]}


def obter_usuario(usuario_id, caminho=None):
    """Revalida uma identidade armazenada na sessão Streamlit."""
    criar_tabela(caminho)
    with closing(conectar(caminho)) as conexao:
        usuario = conexao.execute(
            "SELECT id, nome_usuario, email FROM usuarios WHERE id = ?",
            (usuario_id,),
        ).fetchone()
        return dict(usuario) if usuario else None
