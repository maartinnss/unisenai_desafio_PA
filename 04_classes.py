# ==============================================================================
# UNIDADE CURRICULAR: PROJETO APLICADO I | SCHULZ S.A.
# AV 03 (MVP Parte 1) | Arquivo 04: classes de domínio e conexão SQL
#
# O arquivo tem três partes:
#   1. Exceções próprias: ErroValidacao e ErroPersistencia
#   2. Domínio (POO): Tecnico, Equipamento e Medicao
#   3. Persistência (SQLite): BancoDados, com conexão, CRUD e relatórios
#
# O esquema SQL é o mesmo do 03_banco.sql da Entrega 02.
# ==============================================================================
from __future__ import annotations

import math
import re
import sqlite3
from contextlib import contextmanager
from typing import Iterator, Optional

STATUS_APROVADO = "APROVADO"
STATUS_REPROVADO = "REPROVADO"

# Margem para comparar floats. Sem ela, um limite calculado como 10.0 + 0.1
# (que em binário não é exatamente 10.1) reprovaria uma leitura de 10.1.
EPSILON = 1e-9

_REGEX_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ==============================================================================
# 1. EXCEÇÕES PRÓPRIAS
# ==============================================================================
class ErroValidacao(ValueError):
    """Dado inválido detectado no domínio, antes de chegar ao banco."""


class ErroPersistencia(Exception):
    """Falha de acesso ao SQLite, traduzida para uma mensagem legível."""


# Funções de validação reaproveitadas pelas três entidades.
def _texto(valor, campo: str, minimo: int = 1, maximo: int = 120) -> str:
    if not isinstance(valor, str):
        raise ErroValidacao(f"'{campo}' deve ser um texto.")
    valor = " ".join(valor.split())  # tira espaços duplicados e das pontas
    if not (minimo <= len(valor) <= maximo):
        raise ErroValidacao(
            f"'{campo}' deve ter entre {minimo} e {maximo} caracteres."
        )
    return valor


def _numero(valor, campo: str) -> float:
    """Aceita int, float e texto com vírgula decimal (padrão das planilhas)."""
    if isinstance(valor, bool):
        raise ErroValidacao(f"'{campo}' deve ser numérico.")
    if isinstance(valor, str):
        valor = valor.strip().replace(",", ".")
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ErroValidacao(f"'{campo}' deve ser numérico (recebido: {valor!r}).")
    if math.isnan(numero) or math.isinf(numero):
        raise ErroValidacao(f"'{campo}' deve ser um número finito.")
    return numero


# ==============================================================================
# 2. CLASSES DE DOMÍNIO
# ==============================================================================
class Tecnico:
    """Profissional calibrador (tabela `tecnico`)."""

    def __init__(self, nome_tecnico: str, matricula: str, email: str,
                 setor: str, id_tecnico: Optional[int] = None):
        self._id_tecnico = id_tecnico
        self.nome_tecnico = nome_tecnico
        self.matricula = matricula
        self.email = email
        self.setor = setor

    # O id é gerado pelo banco e só pode ser definido uma vez.
    @property
    def id_tecnico(self) -> Optional[int]:
        return self._id_tecnico

    @id_tecnico.setter
    def id_tecnico(self, valor: int) -> None:
        if self._id_tecnico is not None:
            raise ErroValidacao("id_tecnico já definido e não pode ser alterado.")
        self._id_tecnico = valor

    @property
    def nome_tecnico(self) -> str:
        return self._nome_tecnico

    @nome_tecnico.setter
    def nome_tecnico(self, valor: str) -> None:
        self._nome_tecnico = _texto(valor, "nome_tecnico", minimo=3)

    @property
    def matricula(self) -> str:
        return self._matricula

    @matricula.setter
    def matricula(self, valor: str) -> None:
        valor = _texto(valor, "matricula", minimo=3, maximo=20).upper()
        if not valor.isalnum():
            raise ErroValidacao("'matricula' deve conter apenas letras e números.")
        self._matricula = valor

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, valor: str) -> None:
        valor = _texto(valor, "email", maximo=150).lower()
        if not _REGEX_EMAIL.match(valor):
            raise ErroValidacao(f"'email' inválido: {valor!r}.")
        self._email = valor

    @property
    def setor(self) -> str:
        return self._setor

    @setor.setter
    def setor(self, valor: str) -> None:
        self._setor = _texto(valor, "setor")

    def __repr__(self) -> str:
        return (f"Tecnico(id={self.id_tecnico}, matricula={self.matricula!r}, "
                f"nome={self.nome_tecnico!r}, setor={self.setor!r})")


class Equipamento:
    """Instrumento submetido a calibração (tabela `equipamento`)."""

    def __init__(self, codigo_tag: str, nome_equipamento: str, fabricante: str,
                 modelo: str, id_equipamento: Optional[int] = None):
        self._id_equipamento = id_equipamento
        self.codigo_tag = codigo_tag
        self.nome_equipamento = nome_equipamento
        self.fabricante = fabricante
        self.modelo = modelo

    @property
    def id_equipamento(self) -> Optional[int]:
        return self._id_equipamento

    @id_equipamento.setter
    def id_equipamento(self, valor: int) -> None:
        if self._id_equipamento is not None:
            raise ErroValidacao("id_equipamento já definido e não pode ser alterado.")
        self._id_equipamento = valor

    @property
    def codigo_tag(self) -> str:
        return self._codigo_tag

    @codigo_tag.setter
    def codigo_tag(self, valor: str) -> None:
        valor = _texto(valor, "codigo_tag", minimo=2, maximo=30).upper()
        # As tags da Schulz têm formato como 703.1208 ou 500.011.
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9.\-_/]*", valor):
            raise ErroValidacao(f"'codigo_tag' inválido: {valor!r}.")
        self._codigo_tag = valor

    @property
    def nome_equipamento(self) -> str:
        return self._nome_equipamento

    @nome_equipamento.setter
    def nome_equipamento(self, valor: str) -> None:
        self._nome_equipamento = _texto(valor, "nome_equipamento")

    @property
    def fabricante(self) -> str:
        return self._fabricante

    @fabricante.setter
    def fabricante(self, valor: str) -> None:
        self._fabricante = _texto(valor, "fabricante")

    @property
    def modelo(self) -> str:
        return self._modelo

    @modelo.setter
    def modelo(self, valor: str) -> None:
        self._modelo = _texto(valor, "modelo")

    def __repr__(self) -> str:
        return (f"Equipamento(id={self.id_equipamento}, tag={self.codigo_tag!r}, "
                f"nome={self.nome_equipamento!r})")


class Medicao:
    """Ensaio de calibração (tabela `medicao`).

    Regra do dicionário de dados da Entrega 02:
        tolerancia_min = valor_nominal - |tolerância negativa|
        tolerancia_max = valor_nominal + |tolerância positiva|
        APROVADO  se tolerancia_min <= valor_obtido <= tolerancia_max
        REPROVADO caso contrário

    O status não é um atributo editável: é calculado a cada consulta a partir
    dos limites e do valor obtido, então nunca fica inconsistente com eles.
    """

    def __init__(self, id_equipamento: int, id_tecnico: int,
                 parametro_medido: str, valor_nominal, tolerancia_min,
                 tolerancia_max, valor_obtido,
                 id_medicao: Optional[int] = None,
                 data_medicao: Optional[str] = None):
        self._id_medicao = id_medicao
        self.id_equipamento = id_equipamento
        self.id_tecnico = id_tecnico
        self.parametro_medido = parametro_medido
        # Os limites dependem do nominal, por isso são validados em conjunto.
        self._definir_limites(valor_nominal, tolerancia_min, tolerancia_max)
        self.valor_obtido = valor_obtido
        self.data_medicao = data_medicao  # preenchida pelo banco (CURRENT_TIMESTAMP)

    @classmethod
    def a_partir_de_desvios(cls, id_equipamento: int, id_tecnico: int,
                            parametro_medido: str, valor_nominal,
                            desvio_negativo, desvio_positivo, valor_obtido,
                            **kwargs) -> "Medicao":
        """Cria a medição a partir da notação de desenho (ex.: 10,000 com
        desvios -0,020 e +0,030), convertendo para os limites absolutos
        gravados no banco."""
        nominal = _numero(valor_nominal, "valor_nominal")
        neg = abs(_numero(desvio_negativo, "desvio_negativo"))
        pos = abs(_numero(desvio_positivo, "desvio_positivo"))
        return cls(id_equipamento, id_tecnico, parametro_medido, nominal,
                   nominal - neg, nominal + pos, valor_obtido, **kwargs)

    @property
    def id_medicao(self) -> Optional[int]:
        return self._id_medicao

    @id_medicao.setter
    def id_medicao(self, valor: int) -> None:
        if self._id_medicao is not None:
            raise ErroValidacao("id_medicao já definido e não pode ser alterado.")
        self._id_medicao = valor

    @property
    def id_equipamento(self) -> int:
        return self._id_equipamento

    @id_equipamento.setter
    def id_equipamento(self, valor: int) -> None:
        self._id_equipamento = self._validar_fk(valor, "id_equipamento")

    @property
    def id_tecnico(self) -> int:
        return self._id_tecnico

    @id_tecnico.setter
    def id_tecnico(self, valor: int) -> None:
        self._id_tecnico = self._validar_fk(valor, "id_tecnico")

    @staticmethod
    def _validar_fk(valor, campo: str) -> int:
        if isinstance(valor, bool) or not isinstance(valor, int) or valor <= 0:
            raise ErroValidacao(f"'{campo}' deve ser um inteiro positivo.")
        return valor

    @property
    def parametro_medido(self) -> str:
        return self._parametro_medido

    @parametro_medido.setter
    def parametro_medido(self, valor: str) -> None:
        self._parametro_medido = _texto(valor, "parametro_medido")

    def _definir_limites(self, nominal, minimo, maximo) -> None:
        nominal = _numero(nominal, "valor_nominal")
        minimo = _numero(minimo, "tolerancia_min")
        maximo = _numero(maximo, "tolerancia_max")
        if minimo > maximo + EPSILON:
            raise ErroValidacao(
                "tolerancia_min não pode ser maior que tolerancia_max."
            )
        if not (minimo - EPSILON <= nominal <= maximo + EPSILON):
            raise ErroValidacao(
                "valor_nominal deve estar dentro da faixa "
                "[tolerancia_min, tolerancia_max]."
            )
        self._valor_nominal = nominal
        self._tolerancia_min = minimo
        self._tolerancia_max = maximo

    @property
    def valor_nominal(self) -> float:
        return self._valor_nominal

    @property
    def tolerancia_min(self) -> float:
        return self._tolerancia_min

    @property
    def tolerancia_max(self) -> float:
        return self._tolerancia_max

    def alterar_tolerancias(self, valor_nominal, tolerancia_min,
                            tolerancia_max) -> None:
        """Único caminho para mudar os limites, validando os três juntos."""
        self._definir_limites(valor_nominal, tolerancia_min, tolerancia_max)

    @property
    def valor_obtido(self) -> float:
        return self._valor_obtido

    @valor_obtido.setter
    def valor_obtido(self, valor) -> None:
        self._valor_obtido = _numero(valor, "valor_obtido")

    @property
    def status_resultado(self) -> str:
        """Parecer técnico automático: APROVADO ou REPROVADO."""
        dentro = (self._tolerancia_min - EPSILON
                  <= self._valor_obtido
                  <= self._tolerancia_max + EPSILON)
        return STATUS_APROVADO if dentro else STATUS_REPROVADO

    @property
    def desvio(self) -> float:
        """Valor obtido menos o nominal, com sinal."""
        return self._valor_obtido - self._valor_nominal

    def __repr__(self) -> str:
        return (f"Medicao(id={self.id_medicao}, eq={self.id_equipamento}, "
                f"tec={self.id_tecnico}, {self.parametro_medido!r}, "
                f"obtido={self.valor_obtido}, {self.status_resultado})")


# ==============================================================================
# 3. CAMADA DE PERSISTÊNCIA
# ==============================================================================
_DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tecnico (
    id_tecnico INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_tecnico TEXT NOT NULL,
    matricula TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL,
    setor TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS equipamento (
    id_equipamento INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_tag TEXT NOT NULL UNIQUE,
    nome_equipamento TEXT NOT NULL,
    fabricante TEXT NOT NULL,
    modelo TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS medicao (
    id_medicao INTEGER PRIMARY KEY AUTOINCREMENT,
    id_equipamento INTEGER NOT NULL,
    id_tecnico INTEGER NOT NULL,
    parametro_medido TEXT NOT NULL,
    valor_nominal REAL NOT NULL,
    tolerancia_min REAL NOT NULL,
    tolerancia_max REAL NOT NULL,
    valor_obtido REAL NOT NULL,
    status_resultado TEXT NOT NULL CHECK (status_resultado IN ('APROVADO', 'REPROVADO')),
    data_medicao DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_equipamento) REFERENCES equipamento (id_equipamento)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (id_tecnico) REFERENCES tecnico (id_tecnico)
        ON DELETE RESTRICT ON UPDATE CASCADE
);
"""


class BancoDados:
    """Gerencia a conexão `sqlite3` e executa todos os comandos SQL.

    Os valores sempre entram por parâmetros (`?`), nunca por concatenação de
    texto, o que evita SQL Injection. As escritas rodam em transação: ou
    gravam tudo, ou desfazem (rollback).
    """

    def __init__(self, caminho: str = "schulz_calibracao.db"):
        self.caminho = caminho
        self._conn: Optional[sqlite3.Connection] = None

    # Conexão
    def conectar(self) -> "BancoDados":
        try:
            self._conn = sqlite3.connect(self.caminho)
            self._conn.row_factory = sqlite3.Row
            # O SQLite não aplica chaves estrangeiras por padrão: é preciso
            # ligar o PRAGMA a cada nova conexão.
            self._conn.execute("PRAGMA foreign_keys = ON;")
        except sqlite3.Error as e:
            raise ErroPersistencia(f"Não foi possível abrir '{self.caminho}': {e}")
        return self

    def fechar(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "BancoDados":
        return self.conectar()

    def __exit__(self, *_exc) -> None:
        self.fechar()

    @property
    def conexao(self) -> sqlite3.Connection:
        if self._conn is None:
            raise ErroPersistencia("Banco desconectado. Chame conectar() primeiro.")
        return self._conn

    def criar_esquema(self) -> None:
        try:
            self.conexao.executescript(_DDL)
            self.conexao.execute("PRAGMA foreign_keys = ON;")
        except sqlite3.Error as e:
            raise ErroPersistencia(f"Falha ao criar o esquema: {e}")

    # Execução centralizada, com tradução dos erros do SQLite
    @contextmanager
    def _transacao(self) -> Iterator[sqlite3.Connection]:
        conn = self.conexao
        try:
            with conn:  # commit se der certo, rollback se der erro
                yield conn
        except sqlite3.IntegrityError as e:
            raise ErroPersistencia(self._traduzir_integridade(str(e))) from e
        except sqlite3.Error as e:
            raise ErroPersistencia(f"Erro de banco de dados: {e}") from e

    @staticmethod
    def _traduzir_integridade(msg: str) -> str:
        if "UNIQUE" in msg:
            campo = msg.rsplit(".", 1)[-1]
            return f"Registro duplicado: já existe um registro com este '{campo}'."
        if "FOREIGN KEY" in msg:
            return ("Violação de integridade referencial: o registro referenciado "
                    "não existe ou ainda possui medições vinculadas.")
        if "CHECK" in msg:
            return "Valor rejeitado por uma restrição CHECK do banco."
        if "NOT NULL" in msg:
            return f"Campo obrigatório ausente ({msg})."
        return f"Violação de integridade: {msg}"

    def _consultar(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        try:
            return self.conexao.execute(sql, params).fetchall()
        except sqlite3.Error as e:
            raise ErroPersistencia(f"Erro ao consultar: {e}") from e

    # ==========================================================================
    # Técnico
    # ==========================================================================
    @staticmethod
    def _linha_para_tecnico(r: sqlite3.Row) -> Tecnico:
        return Tecnico(r["nome_tecnico"], r["matricula"], r["email"],
                       r["setor"], id_tecnico=r["id_tecnico"])

    def inserir_tecnico(self, t: Tecnico) -> int:
        with self._transacao() as c:
            cur = c.execute(
                "INSERT INTO tecnico (nome_tecnico, matricula, email, setor) "
                "VALUES (?, ?, ?, ?)",
                (t.nome_tecnico, t.matricula, t.email, t.setor))
        t.id_tecnico = cur.lastrowid
        return cur.lastrowid

    def buscar_tecnico(self, id_tecnico: int) -> Optional[Tecnico]:
        rows = self._consultar("SELECT * FROM tecnico WHERE id_tecnico = ?",
                               (id_tecnico,))
        return self._linha_para_tecnico(rows[0]) if rows else None

    def buscar_tecnico_por_matricula(self, matricula: str) -> Optional[Tecnico]:
        rows = self._consultar("SELECT * FROM tecnico WHERE matricula = ?",
                               (matricula.strip().upper(),))
        return self._linha_para_tecnico(rows[0]) if rows else None

    def listar_tecnicos(self) -> list[Tecnico]:
        return [self._linha_para_tecnico(r) for r in
                self._consultar("SELECT * FROM tecnico ORDER BY nome_tecnico")]

    def atualizar_tecnico(self, t: Tecnico) -> bool:
        self._exigir_id(t.id_tecnico, "Tecnico")
        with self._transacao() as c:
            cur = c.execute(
                "UPDATE tecnico SET nome_tecnico = ?, matricula = ?, email = ?, "
                "setor = ? WHERE id_tecnico = ?",
                (t.nome_tecnico, t.matricula, t.email, t.setor, t.id_tecnico))
        return cur.rowcount > 0

    def remover_tecnico(self, id_tecnico: int) -> bool:
        with self._transacao() as c:
            cur = c.execute("DELETE FROM tecnico WHERE id_tecnico = ?",
                            (id_tecnico,))
        return cur.rowcount > 0

    # ==========================================================================
    # Equipamento
    # ==========================================================================
    @staticmethod
    def _linha_para_equipamento(r: sqlite3.Row) -> Equipamento:
        return Equipamento(r["codigo_tag"], r["nome_equipamento"],
                           r["fabricante"], r["modelo"],
                           id_equipamento=r["id_equipamento"])

    def inserir_equipamento(self, e: Equipamento) -> int:
        with self._transacao() as c:
            cur = c.execute(
                "INSERT INTO equipamento (codigo_tag, nome_equipamento, "
                "fabricante, modelo) VALUES (?, ?, ?, ?)",
                (e.codigo_tag, e.nome_equipamento, e.fabricante, e.modelo))
        e.id_equipamento = cur.lastrowid
        return cur.lastrowid

    def buscar_equipamento(self, id_equipamento: int) -> Optional[Equipamento]:
        rows = self._consultar(
            "SELECT * FROM equipamento WHERE id_equipamento = ?",
            (id_equipamento,))
        return self._linha_para_equipamento(rows[0]) if rows else None

    def buscar_equipamento_por_tag(self, codigo_tag: str) -> Optional[Equipamento]:
        rows = self._consultar("SELECT * FROM equipamento WHERE codigo_tag = ?",
                               (codigo_tag.strip().upper(),))
        return self._linha_para_equipamento(rows[0]) if rows else None

    def listar_equipamentos(self) -> list[Equipamento]:
        return [self._linha_para_equipamento(r) for r in
                self._consultar("SELECT * FROM equipamento ORDER BY codigo_tag")]

    def atualizar_equipamento(self, e: Equipamento) -> bool:
        self._exigir_id(e.id_equipamento, "Equipamento")
        with self._transacao() as c:
            cur = c.execute(
                "UPDATE equipamento SET codigo_tag = ?, nome_equipamento = ?, "
                "fabricante = ?, modelo = ? WHERE id_equipamento = ?",
                (e.codigo_tag, e.nome_equipamento, e.fabricante, e.modelo,
                 e.id_equipamento))
        return cur.rowcount > 0

    def remover_equipamento(self, id_equipamento: int) -> bool:
        with self._transacao() as c:
            cur = c.execute("DELETE FROM equipamento WHERE id_equipamento = ?",
                            (id_equipamento,))
        return cur.rowcount > 0

    # ==========================================================================
    # Medição
    # ==========================================================================
    @staticmethod
    def _linha_para_medicao(r: sqlite3.Row) -> Medicao:
        return Medicao(r["id_equipamento"], r["id_tecnico"],
                       r["parametro_medido"], r["valor_nominal"],
                       r["tolerancia_min"], r["tolerancia_max"],
                       r["valor_obtido"], id_medicao=r["id_medicao"],
                       data_medicao=r["data_medicao"])

    def inserir_medicao(self, m: Medicao) -> int:
        # O status gravado vem da regra da classe, não de quem chama.
        with self._transacao() as c:
            cur = c.execute(
                "INSERT INTO medicao (id_equipamento, id_tecnico, "
                "parametro_medido, valor_nominal, tolerancia_min, "
                "tolerancia_max, valor_obtido, status_resultado) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (m.id_equipamento, m.id_tecnico, m.parametro_medido,
                 m.valor_nominal, m.tolerancia_min, m.tolerancia_max,
                 m.valor_obtido, m.status_resultado))
        m.id_medicao = cur.lastrowid
        m.data_medicao = self._consultar(
            "SELECT data_medicao FROM medicao WHERE id_medicao = ?",
            (cur.lastrowid,))[0]["data_medicao"]
        return cur.lastrowid

    def buscar_medicao(self, id_medicao: int) -> Optional[Medicao]:
        rows = self._consultar("SELECT * FROM medicao WHERE id_medicao = ?",
                               (id_medicao,))
        return self._linha_para_medicao(rows[0]) if rows else None

    def listar_medicoes(self) -> list[Medicao]:
        return [self._linha_para_medicao(r) for r in
                self._consultar("SELECT * FROM medicao ORDER BY id_medicao")]

    def atualizar_medicao(self, m: Medicao) -> bool:
        """Regrava o ensaio com o status recalculado pelos novos valores."""
        self._exigir_id(m.id_medicao, "Medicao")
        with self._transacao() as c:
            cur = c.execute(
                "UPDATE medicao SET id_equipamento = ?, id_tecnico = ?, "
                "parametro_medido = ?, valor_nominal = ?, tolerancia_min = ?, "
                "tolerancia_max = ?, valor_obtido = ?, status_resultado = ? "
                "WHERE id_medicao = ?",
                (m.id_equipamento, m.id_tecnico, m.parametro_medido,
                 m.valor_nominal, m.tolerancia_min, m.tolerancia_max,
                 m.valor_obtido, m.status_resultado, m.id_medicao))
        return cur.rowcount > 0

    def remover_medicao(self, id_medicao: int) -> bool:
        with self._transacao() as c:
            cur = c.execute("DELETE FROM medicao WHERE id_medicao = ?",
                            (id_medicao,))
        return cur.rowcount > 0

    # ==========================================================================
    # Consultas relacionais (JOIN)
    # ==========================================================================
    def relatorio_calibracao(self, status: Optional[str] = None,
                             codigo_tag: Optional[str] = None) -> list[dict]:
        """Relatório de calibração: medição, equipamento e técnico (INNER JOIN).

        Aceita filtros opcionais por status e por tag, sempre parametrizados."""
        sql = (
            "SELECT m.id_medicao, e.codigo_tag, e.nome_equipamento, "
            "       m.parametro_medido, m.valor_nominal, m.tolerancia_min, "
            "       m.tolerancia_max, m.valor_obtido, m.status_resultado, "
            "       t.nome_tecnico, t.matricula, m.data_medicao "
            "FROM medicao m "
            "INNER JOIN equipamento e ON e.id_equipamento = m.id_equipamento "
            "INNER JOIN tecnico t     ON t.id_tecnico     = m.id_tecnico "
            "WHERE 1 = 1 "
        )
        params: list = []
        if status is not None:
            status = status.strip().upper()
            if status not in (STATUS_APROVADO, STATUS_REPROVADO):
                raise ErroValidacao(
                    f"status deve ser {STATUS_APROVADO} ou {STATUS_REPROVADO}.")
            sql += "AND m.status_resultado = ? "
            params.append(status)
        if codigo_tag is not None:
            sql += "AND e.codigo_tag = ? "
            params.append(codigo_tag.strip().upper())
        sql += "ORDER BY e.codigo_tag, m.id_medicao"
        return [dict(r) for r in self._consultar(sql, tuple(params))]

    def resumo_por_equipamento(self) -> list[dict]:
        """Totais de aprovadas e reprovadas por equipamento (LEFT JOIN com
        GROUP BY). Equipamentos ainda sem medição aparecem com zero."""
        sql = (
            "SELECT e.codigo_tag, e.nome_equipamento, "
            "       COUNT(m.id_medicao) AS total, "
            "       COALESCE(SUM(m.status_resultado = 'APROVADO'), 0)  AS aprovadas, "
            "       COALESCE(SUM(m.status_resultado = 'REPROVADO'), 0) AS reprovadas "
            "FROM equipamento e "
            "LEFT JOIN medicao m ON m.id_equipamento = e.id_equipamento "
            "GROUP BY e.id_equipamento ORDER BY e.codigo_tag"
        )
        return [dict(r) for r in self._consultar(sql)]

    @staticmethod
    def _exigir_id(valor, entidade: str) -> None:
        if valor is None:
            raise ErroValidacao(
                f"{entidade} ainda não foi gravado (sem id). Use inserir_* antes.")
