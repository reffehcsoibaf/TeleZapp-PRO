# SPDX-License-Identifier: GPL-3.0-or-later
"""Extensões do TeleZapp PRO.

Uma extensão é uma pasta dentro de `extensoes\\` com um arquivo `extensao.py` que tem a função
`registrar(api)`. O PRO carrega as extensões ao montar o menu; o que a extensão pede (menus,
atalhos) aparece como um submenu próprio. Uma extensão com erro NUNCA impede o PRO de abrir:
o erro vai para o log e o PRO segue sem ela.

O que a extensão recebe (`api`):
  api.nome / api.pasta         nome e pasta da extensão
  api.janela                   a janela principal (pai das janelas da extensão)
  api.banco                    o banco do PRO (só para ler; use o que a janela oferece para gravar)
  api.pasta_dados              pasta própria para os dados da extensão (criada se faltar)
  api.falar(texto)             fala pelo leitor de tela
  api.conversa_selecionada()   dict da conversa marcada na lista ou None:
                               conta_id, conversa_id, nome, tipo, servico, telefone,
                               primeira_mensagem (dia AAAA-MM-DD da mensagem mais antiga guardada, ou '')
  api.conversas_privadas()     conversas privadas do WhatsApp com telefone (dicts como acima, sem primeira_mensagem)
  api.abrir_conversa(conta_id, conversa_id)   abre a conversa na janela principal (feche antes as janelas modais)
  api.adicionar_menu(titulo, itens)
        titulo: texto do submenu, com & no atalho de letra (ex.: "&Comercial")
        itens:  lista de (id, rótulo, atalho_padrao, função); atalho_padrao pode ser ""
                (uma linha ("-",) vira separador). O usuário muda os atalhos em
                "Personalizar os atalhos" como os de qualquer outro item.

Limite atual: os módulos da extensão são importados soltos (a pasta dela entra no sys.path);
duas extensões não podem ter módulos com o mesmo nome."""
import importlib.util
import logging
import re
import sys
import traceback
from datetime import datetime
from pathlib import Path

log = logging.getLogger("telezapp.extensoes")

PASTA = Path(__file__).resolve().parents[2] / "extensoes"


class Api:
    def __init__(self, nome, pasta, janela):
        self.nome, self.pasta, self.janela = nome, pasta, janela
        self.menus = []                      # [(titulo, [(id, rotulo, atalho, funcao)])]

    @property
    def banco(self):
        return self.janela.banco

    @property
    def pasta_dados(self):
        from telezapp import config
        p = Path(config.pasta_dados()) / "extensoes" / self.nome
        p.mkdir(parents=True, exist_ok=True)
        return p

    def falar(self, texto, interromper=True):
        self.janela.fala.falar(texto, interromper)

    def adicionar_menu(self, titulo, itens):
        self.menus.append((titulo, list(itens)))

    def conversa_selecionada(self):
        conv = self.janela._conversa_selecionada()
        if conv is None:
            return None
        return {"conta_id": conv.conta_id, "conversa_id": conv.id, "nome": conv.nome, "tipo": conv.tipo,
                "servico": conv.servico, "telefone": self._telefone(conv),
                "primeira_mensagem": self._primeira_mensagem(conv)}

    def conversas_privadas(self, servico="whatsapp"):
        """Lista de dicts (conta_id, conversa_id, nome, tipo, servico, telefone) das conversas privadas
        do serviço que têm telefone, para a extensão achar a conversa de um telefone."""
        agenda = {}
        try:
            for conta, id_, _nome, telefone in self.banco.contatos():
                agenda[(conta, id_)] = re.sub(r"\D", "", telefone or "")
        except Exception:  # noqa: BLE001
            log.warning("não consegui ler a agenda", exc_info=True)
        achadas = []
        for conv in list(self.janela.indice.values()):
            if conv.tipo != "privada" or (servico and conv.servico != servico):
                continue
            antes, _, depois = conv.id.partition("@")
            if depois == "s.whatsapp.net":
                tel = re.sub(r"\D", "", antes)
            else:
                tel = agenda.get((conv.conta_id, conv.id), "")
            if tel:
                achadas.append({"conta_id": conv.conta_id, "conversa_id": conv.id, "nome": conv.nome,
                                "tipo": conv.tipo, "servico": conv.servico, "telefone": tel})
        return achadas

    def abrir_conversa(self, conta_id, conversa_id):
        """Abre a conversa na janela principal. Só vale com as janelas da extensão já fechadas."""
        conv = self.janela.indice.get((conta_id, conversa_id))
        if conv is None:
            self.falar("Esta conversa não está na lista do TeleZapp PRO.")
            return False
        self.janela._abrir_conversa_de(conv)
        return True

    def _primeira_mensagem(self, conv):
        """Dia (AAAA-MM-DD, no horário do computador) da mensagem mais antiga guardada, ou ''."""
        try:
            quando = self.banco.data_primeira_mensagem(conv.conta_id, conv.id)
            return datetime.fromtimestamp(quando).strftime("%Y-%m-%d") if quando else ""
        except Exception:  # noqa: BLE001
            log.warning("não consegui ler a data da primeira mensagem", exc_info=True)
            return ""

    def _telefone(self, conv):
        """Dígitos do telefone, ou '' se não der para saber (grupo, canal, Telegram sem número)."""
        if conv.tipo != "privada":
            return ""
        antes, _, depois = conv.id.partition("@")
        if depois == "s.whatsapp.net":
            return re.sub(r"\D", "", antes)
        try:                                 # conversas por LID: o número está na agenda
            for _conta, id_, _nome, telefone in self.banco.contatos(conv.conta_id):
                if id_ == conv.id:
                    return re.sub(r"\D", "", telefone or "")
        except Exception:  # noqa: BLE001
            log.warning("não consegui ler a agenda para achar o telefone", exc_info=True)
        return ""


def _carregar_modulo(pasta):
    arq = pasta / "extensao.py"
    if str(pasta) not in sys.path:
        sys.path.insert(0, str(pasta))
    spec = importlib.util.spec_from_file_location("telezapp_ext_" + pasta.name, arq)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def carregar(janela, pasta=None):
    """Carrega as extensões e devolve a lista de Api (com os menus que cada uma pediu)."""
    pasta = Path(pasta) if pasta else PASTA
    apis = []
    if not pasta.is_dir():
        return apis
    for d in sorted(pasta.iterdir()):
        if not (d.is_dir() and (d / "extensao.py").is_file()) or d.name.startswith(("_", ".")):
            continue
        api = Api(d.name, d, janela)
        try:
            modulo = _carregar_modulo(d)
            modulo.registrar(api)
        except Exception:  # noqa: BLE001
            log.error("a extensão %s falhou ao carregar e foi ignorada:\n%s", d.name, traceback.format_exc())
            continue
        apis.append(api)
        log.info("extensão %s carregada", d.name)
    return apis
