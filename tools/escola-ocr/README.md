# escola-ocr — das fotos do livro aos exercícios

Ferramenta de dados do Estudo Moedas. Pega nas fotos das páginas do livro da escola, tira o texto
(OCR do Windows), manda esse texto a um modelo barato para limpar e separar os enunciados, e guarda
tudo numa base SQLite local (`escola.db`). É daqui que saem os exercícios reais que o app usa.

Não é servidor nem app: corre à mão, quando se quer acrescentar páginas.

## Como está montado (4 passos)

1. **Fotos** — as páginas vivem em `extracao/<matéria>/`, uma pasta por matéria
   (`castellano`, `galego`, `ingles`, `mates`, `sociais`).
2. **`escola_db.py sync`** — regista as fotos na base (matérias → documentos → páginas).
3. **`escola_db.py ocr`** — corre o OCR do Windows (`ocr_winrt.ps1`) e guarda o texto cru em
   `page_text`. Nada é inventado: se o OCR falha, a página fica marcada e segue.
4. **`extract.py`** — manda o texto ao modelo (gemini-2.5-flash; reserva deepseek-v4-flash), que devolve
   `{"texto_corregido": ..., "ejercicios": [...]}`; grava o JSON cru e o número de exercícios em
   `page_extract`. A resposta (`respuesta`) só se guarda quando sai do texto da página — caligrafia
   não é fonte fiável, por isso muitas ficam vazias e o exercício não entra no app.

## Comandos

```bash
cd tools/escola-ocr
python escola_db.py sync          # fotos -> base
python escola_db.py ocr [limite]  # OCR das páginas que ainda não têm texto
python escola_db.py stats         # fotos, páginas, chars por matéria
python escola_db.py export        # exercícios corrigíveis -> ../../content/ejercicios-libro.json
python extract.py [matéria] [n]   # páginas pendentes -> exercícios (sem limite = todas)
python extract.py redo <matéria>  # apaga o extrato dessa matéria e extrai de novo
python extract.py stats           # cobertura por matéria
python contact_sheet.py           # folha de contactos das páginas (conferência visual)
```

Chave do OpenRouter: `OPENROUTER_API_KEY` no ambiente, ou no `.env` do Hermes
(`ESCOLA_OCR_ENV` aponta para outro ficheiro, se quiseres).

## Estado atual (18/11/2026)

- 5 matérias, 47 páginas com texto OCR, **232 exercícios** extraídos, **143 corrigíveis** (com resposta).
- O app lê `content/ejercicios-libro.json` (gerado por `escola_db.py export`): escolha múltipla quando
  a resposta está entre ≥3 opções; nos restantes casos entra como resposta escrita (`tipo:"escri"`).
  Só entram exercícios com resposta — o que não se pode corrigir não se mostra.
- Por matéria corrigível: mates 96, castellano 41, galego 6; inglês e sociais 0 (páginas de atividades
  visuais, sem resposta no texto).

## O que NÃO vai para o git

`extracao/`, `state/` e `escola.db` estão no `.gitignore`: são fotos do livro e dados da criança.
O repositório guarda só o código e o esquema (`schema.sql`).
