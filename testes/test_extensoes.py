# SPDX-License-Identifier: GPL-3.0-or-later
"""Carregador de extensões: carrega, junta os menus e ignora a que dá erro."""
from types import SimpleNamespace

from telezapp.nucleo import extensoes


def _ext(pasta, nome, codigo):
    d = pasta / nome
    d.mkdir()
    (d / "extensao.py").write_text(codigo, encoding="utf-8")


def test_carrega_e_junta_menus(tmp_path):
    _ext(tmp_path, "boa", "def registrar(api):\n"
         "    api.adicionar_menu('&Boa', [('a', '&A', 'Ctrl+1', lambda: 1), ('-',)])\n")
    apis = extensoes.carregar(SimpleNamespace(), tmp_path)
    assert [a.nome for a in apis] == ["boa"]
    assert apis[0].menus[0][0] == "&Boa"
    assert apis[0].menus[0][1][0][3]() == 1


def test_extensao_com_erro_nao_derruba(tmp_path):
    _ext(tmp_path, "a_ruim", "raise RuntimeError('x')\n")
    _ext(tmp_path, "b_ruim", "def registrar(api):\n    raise RuntimeError('y')\n")
    _ext(tmp_path, "c_boa", "def registrar(api):\n    api.adicionar_menu('&C', [])\n")
    _ext(tmp_path, "_ignorada", "def registrar(api):\n    api.adicionar_menu('&I', [])\n")
    apis = extensoes.carregar(SimpleNamespace(), tmp_path)
    assert [a.nome for a in apis] == ["c_boa"]


def test_pasta_inexistente(tmp_path):
    assert extensoes.carregar(SimpleNamespace(), tmp_path / "nao_existe") == []


def _janela_falsa(conversas, agenda=()):
    janela = SimpleNamespace(
        indice={(c.conta_id, c.id): c for c in conversas},
        banco=SimpleNamespace(contatos=lambda conta_id=None: list(agenda)),
        abertas=[], fala=SimpleNamespace(falar=lambda *a, **k: None))
    janela._abrir_conversa_de = janela.abertas.append
    return janela


def _conv(id_, nome, tipo="privada", servico="whatsapp", conta="c1"):
    return SimpleNamespace(conta_id=conta, id=id_, nome=nome, tipo=tipo, servico=servico)


def test_conversas_privadas_e_abrir(tmp_path):
    a = _conv("5551999990000@s.whatsapp.net", "Ana")
    lid = _conv("123@lid", "Beto")
    grupo = _conv("g@g.us", "Grupo", tipo="grupo")
    tg = _conv("42", "Carla", servico="telegram")
    janela = _janela_falsa([a, lid, grupo, tg], agenda=[("c1", "123@lid", "Beto", "+55 51 98888-7777")])
    api = extensoes.Api("x", tmp_path, janela)
    achadas = api.conversas_privadas()
    assert {(c["nome"], c["telefone"]) for c in achadas} == {("Ana", "5551999990000"), ("Beto", "5551988887777")}
    assert api.abrir_conversa("c1", a.id) is True
    assert janela.abertas == [a]
    assert api.abrir_conversa("c1", "nao existe") is False
