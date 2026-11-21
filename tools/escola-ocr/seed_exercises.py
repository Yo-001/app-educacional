#!/usr/bin/env python3
"""Semeadura idempotente de exercicios curriculares (3º/4º Primaria - Galiza/Espanha)."""
import json
import os
import re
import sqlite3
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(ROOT, "escola.db")
NOW = lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

EXERCISES = [
    # ==================== GALEGO (14) ====================
    {
        "slug": "galego", "unit": "Vocabulario", "topic": "animais", "difficulty": 1,
        "statement": "Como se chama en galego a cría da vaca?",
        "answer": "becerro",
        "options": ["becerro", "cordeiro", "poldro", "leitón"],
    },
    {
        "slug": "galego", "unit": "Vocabulario", "topic": "días da semana", "difficulty": 1,
        "statement": "Cal é o primeiro día da semana despois do domingo?",
        "answer": "luns",
        "options": ["luns", "martes", "mércores", "venres"],
    },
    {
        "slug": "galego", "unit": "Gramática", "topic": "artigos", "difficulty": 1,
        "statement": "Completa co artigo correcto: «___ árbore do xardín é moi alta».",
        "answer": "A",
        "options": ["A", "O", "Os", "Un"],
    },
    {
        "slug": "galego", "unit": "Vocabulario", "topic": "antónimos", "difficulty": 1,
        "statement": "Cal é o antónimo da palabra «quente» en galego?",
        "answer": "frío",
        "options": ["frío", "morna", "ardente", "seco"],
    },
    {
        "slug": "galego", "unit": "Ortografía", "topic": "b e v", "difficulty": 2,
        "statement": "Que palabra está escrita correctamente en galego?",
        "answer": "avó",
        "options": ["avó", "abó", "avoo", "habó"],
    },
    {
        "slug": "galego", "unit": "Gramática", "topic": "plural", "difficulty": 2,
        "statement": "Escribe o plural da palabra galega «can».",
        "answer": "cans",
        "options": None,
    },
    {
        "slug": "galego", "unit": "Gramática", "topic": "plural", "difficulty": 2,
        "statement": "Cal é o plural correcto da palabra «xornal»?",
        "answer": "xornais",
        "options": ["xornais", "xornales", "xornals", "xornás"],
    },
    {
        "slug": "galego", "unit": "Vocabulario", "topic": "meses", "difficulty": 1,
        "statement": "Como se chama en galego o primeiro mes do ano?",
        "answer": "xaneiro",
        "options": None,
    },
    {
        "slug": "galego", "unit": "Ortografía", "topic": "dígrafos", "difficulty": 2,
        "statement": "Que palabra galega leva «ll» e significa parte da planta?",
        "answer": "folla",
        "options": ["folla", "foya", "fola", "follia"],
    },
    {
        "slug": "galego", "unit": "Vocabulario", "topic": "sinónimos", "difficulty": 2,
        "statement": "Cal é un sinónimo de «ledicia» en galego?",
        "answer": "alegría",
        "options": ["alegría", "tristeza", "medo", "rabia"],
    },
    {
        "slug": "galego", "unit": "Gramática", "topic": "xénero", "difficulty": 2,
        "statement": "Cal é o feminino de «rei» en galego?",
        "answer": "raíña",
        "options": ["raíña", "reia", "princesa", "duquesa"],
    },
    {
        "slug": "galego", "unit": "Gramática", "topic": "verbos", "difficulty": 3,
        "statement": "Completa co verbo correcto: «Onte nós ___ ao museo».",
        "answer": "fomos",
        "options": ["fomos", "imos", "iremos", "vamos"],
    },
    {
        "slug": "galego", "unit": "Ortografía", "topic": "acentuación", "difficulty": 3,
        "statement": "Cal destas palabras é esdrúxula en galego?",
        "answer": "lámpara",
        "options": ["lámpara", "camión", "xardín", "caderno"],
    },
    {
        "slug": "galego", "unit": "Vocabulario", "topic": "natureza", "difficulty": 3,
        "statement": "Como se chama en galego a auga que cae das nubes en forma de pequenas bólas de xeo?",
        "answer": "sarabia",
        "options": ["sarabia", "orballo", "néboa", "brétema"],
    },

    # ==================== INGLES (14) ====================
    {
        "slug": "ingles", "unit": "Grammar", "topic": "to be", "difficulty": 1,
        "statement": "Complete the sentence: «She ___ my best friend.»",
        "answer": "is",
        "options": ["is", "are", "am", "be"],
    },
    {
        "slug": "ingles", "unit": "Vocabulary", "topic": "days of the week", "difficulty": 1,
        "statement": "Which day comes after Tuesday?",
        "answer": "Wednesday",
        "options": ["Wednesday", "Monday", "Thursday", "Sunday"],
    },
    {
        "slug": "ingles", "unit": "Vocabulary", "topic": "animals", "difficulty": 1,
        "statement": "Which animal lives in the sea and has eight arms?",
        "answer": "octopus",
        "options": ["octopus", "giraffe", "rabbit", "eagle"],
    },
    {
        "slug": "ingles", "unit": "Vocabulary", "topic": "numbers", "difficulty": 1,
        "statement": "Write in English the number 15.",
        "answer": "fifteen",
        "options": None,
    },
    {
        "slug": "ingles", "unit": "Vocabulary", "topic": "months", "difficulty": 1,
        "statement": "Which is the last month of the year in English?",
        "answer": "December",
        "options": ["December", "January", "November", "October"],
    },
    {
        "slug": "ingles", "unit": "Grammar", "topic": "have got", "difficulty": 2,
        "statement": "Choose the right option: «A bird ___ got wings.»",
        "answer": "has",
        "options": ["has", "have", "is", "do"],
    },
    {
        "slug": "ingles", "unit": "Grammar", "topic": "can / can't", "difficulty": 2,
        "statement": "Complete the sentence: «Fish can swim, but they ___ fly.»",
        "answer": "can't",
        "options": ["can't", "can", "aren't", "hasn't"],
    },
    {
        "slug": "ingles", "unit": "Vocabulary", "topic": "food", "difficulty": 2,
        "statement": "Which of these foods is a vegetable?",
        "answer": "carrot",
        "options": ["carrot", "apple", "cheese", "bread"],
    },
    {
        "slug": "ingles", "unit": "Grammar", "topic": "plurals", "difficulty": 2,
        "statement": "What is the plural of «child» in English?",
        "answer": "children",
        "options": ["children", "childs", "childes", "childrens"],
    },
    {
        "slug": "ingles", "unit": "Vocabulary", "topic": "weather", "difficulty": 2,
        "statement": "Complete: «Take your umbrella! It is ___ today.»",
        "answer": "raining",
        "options": ["raining", "sunny", "hot", "dry"],
    },
    {
        "slug": "ingles", "unit": "Grammar", "topic": "prepositions", "difficulty": 3,
        "statement": "Complete with the correct preposition: «My birthday is ___ May.»",
        "answer": "in",
        "options": ["in", "on", "at", "under"],
    },
    {
        "slug": "ingles", "unit": "Grammar", "topic": "present simple", "difficulty": 3,
        "statement": "Choose the correct verb form: «Tom ___ football every Saturday.»",
        "answer": "plays",
        "options": ["plays", "play", "playing", "to play"],
    },
    {
        "slug": "ingles", "unit": "Vocabulary", "topic": "time", "difficulty": 3,
        "statement": "How do you say «Son las tres y media» in English?",
        "answer": "half past three",
        "options": ["half past three", "three o'clock", "quarter to three", "quarter past three"],
    },
    {
        "slug": "ingles", "unit": "Vocabulary", "topic": "opposites", "difficulty": 2,
        "statement": "Write the opposite of the adjective «fast» in English.",
        "answer": "slow",
        "options": None,
    },

    # ==================== SOCIAIS (14) ====================
    {
        "slug": "sociais", "unit": "Galicia", "topic": "provincias", "difficulty": 1,
        "statement": "¿Cuántas provincias tiene la comunidad autónoma de Galicia?",
        "answer": "4",
        "options": None,
    },
    {
        "slug": "sociais", "unit": "Galicia", "topic": "capital", "difficulty": 1,
        "statement": "¿Cuál es la capital de Galicia?",
        "answer": "Santiago de Compostela",
        "options": ["Santiago de Compostela", "A Coruña", "Vigo", "Lugo"],
    },
    {
        "slug": "sociais", "unit": "Orientación", "topic": "puntos cardinales", "difficulty": 1,
        "statement": "¿Por qué punto cardinal sale el Sol cada mañana?",
        "answer": "Este",
        "options": ["Este", "Oeste", "Norte", "Sur"],
    },
    {
        "slug": "sociais", "unit": "Galicia", "topic": "provincias", "difficulty": 1,
        "statement": "¿Cuál de estas provincias gallegas NO tiene costa?",
        "answer": "Ourense",
        "options": ["Ourense", "Pontevedra", "A Coruña", "Lugo"],
    },
    {
        "slug": "sociais", "unit": "El Universo", "topic": "sistema solar", "difficulty": 1,
        "statement": "¿Cómo se llama el único satélite natural de la Tierra?",
        "answer": "Luna",
        "options": None,
    },
    {
        "slug": "sociais", "unit": "Geografía", "topic": "océanos y mares", "difficulty": 2,
        "statement": "¿Qué océano baña la costa oeste de Galicia?",
        "answer": "Océano Atlántico",
        "options": ["Océano Atlántico", "Mar Mediterráneo", "Océano Pacífico", "Océano Índico"],
    },
    {
        "slug": "sociais", "unit": "Geografía", "topic": "ríos de Galicia", "difficulty": 2,
        "statement": "¿Cuál es el río más largo de Galicia?",
        "answer": "Miño",
        "options": ["Miño", "Ebro", "Duero", "Guadalquivir"],
    },
    {
        "slug": "sociais", "unit": "La Tierra", "topic": "movimientos", "difficulty": 2,
        "statement": "¿Qué movimiento de la Tierra dura 24 horas y produce el día y la noche?",
        "answer": "Rotación",
        "options": ["Rotación", "Traslación", "Erupción", "Inclinación"],
    },
    {
        "slug": "sociais", "unit": "España", "topic": "geografía política", "difficulty": 2,
        "statement": "¿Con qué país limita Galicia por el sur?",
        "answer": "Portugal",
        "options": ["Portugal", "Francia", "Andorra", "Marruecos"],
    },
    {
        "slug": "sociais", "unit": "Sectores económicos", "topic": "trabajos", "difficulty": 2,
        "statement": "¿A qué sector pertenece la pesca y la agricultura?",
        "answer": "Sector primario",
        "options": ["Sector primario", "Sector secundario", "Sector terciario", "Sector digital"],
    },
    {
        "slug": "sociais", "unit": "El tiempo y clima", "topic": "instrumentos", "difficulty": 3,
        "statement": "¿Qué instrumento sirve para medir la cantidad de lluvia que cae?",
        "answer": "Pluviómetro",
        "options": ["Pluviómetro", "Termómetro", "Veleta", "Brújula"],
    },
    {
        "slug": "sociais", "unit": "El Universo", "topic": "sistema solar", "difficulty": 3,
        "statement": "¿Cuál es el planeta más grande del sistema solar?",
        "answer": "Júpiter",
        "options": ["Júpiter", "Saturno", "Marte", "Venus"],
    },
    {
        "slug": "sociais", "unit": "Historia", "topic": "edades históricas", "difficulty": 3,
        "statement": "¿Qué invento marcó el final de la Prehistoria y el inicio de la Historia?",
        "answer": "La escritura",
        "options": ["La escritura", "La electricidad", "El automóvil", "El teléfono"],
    },
    {
        "slug": "sociais", "unit": "Relieve", "topic": "paisaje", "difficulty": 2,
        "statement": "¿Cómo se llama una porción de tierra rodeada de agua por todas partes menos por una?",
        "answer": "Península",
        "options": ["Península", "Isla", "Archipiélago", "Cabo"],
    },

    # ==================== NATURAIS (14) ====================
    {
        "slug": "naturais", "unit": "Los animales", "topic": "clasificación", "difficulty": 1,
        "statement": "¿Cómo se llaman los animales que tienen columna vertebral?",
        "answer": "Vertebrados",
        "options": ["Vertebrados", "Invertebrados", "Moluscos", "Insectos"],
    },
    {
        "slug": "naturais", "unit": "Los animales", "topic": "reproducción", "difficulty": 1,
        "statement": "¿Cómo se llaman los animales que nacen de un huevo?",
        "answer": "Ovíparos",
        "options": ["Ovíparos", "Vivíparos", "Herbívoros", "Omnívoros"],
    },
    {
        "slug": "naturais", "unit": "Las plantas", "topic": "partes de la planta", "difficulty": 1,
        "statement": "¿Qué parte de la planta absorbe el agua y las sales minerales del suelo?",
        "answer": "La raíz",
        "options": ["La raíz", "El tallo", "La hoja", "La flor"],
    },
    {
        "slug": "naturais", "unit": "El cuerpo humano", "topic": "sentidos", "difficulty": 1,
        "statement": "¿Cuál es el órgano principal del sentido del oído?",
        "answer": "El oído",
        "options": ["El oído", "La lengua", "La piel", "La nariz"],
    },
    {
        "slug": "naturais", "unit": "La materia", "topic": "estados del agua", "difficulty": 1,
        "statement": "¿En qué estado se encuentra el agua cuando forma hielo?",
        "answer": "Sólido",
        "options": ["Sólido", "Líquido", "Gaseoso", "Vapor"],
    },
    {
        "slug": "naturais", "unit": "Las plantas", "topic": "fotosíntesis", "difficulty": 2,
        "statement": "¿Cómo se llama el proceso por el que las plantas fabrican su propio alimento con luz solar?",
        "answer": "Fotosíntesis",
        "options": ["Fotosíntesis", "Digestión", "Respiración", "Evaporación"],
    },
    {
        "slug": "naturais", "unit": "El cuerpo humano", "topic": "aparatos", "difficulty": 2,
        "statement": "¿Qué órgano bombea la sangre por todo el cuerpo?",
        "answer": "El corazón",
        "options": ["El corazón", "El estómago", "El pulmón", "El hígado"],
    },
    {
        "slug": "naturais", "unit": "El cuerpo humano", "topic": "aparatos", "difficulty": 2,
        "statement": "¿Cómo se llaman los dos órganos principales con los que respiramos?",
        "answer": "Pulmones",
        "options": None,
    },
    {
        "slug": "naturais", "unit": "Los animales", "topic": "alimentación", "difficulty": 2,
        "statement": "¿Cómo se llama un animal que come tanto plantas como carne?",
        "answer": "Omnívoro",
        "options": ["Omnívoro", "Carnívoro", "Herbívoro", "Descomponedor"],
    },
    {
        "slug": "naturais", "unit": "Los animales", "topic": "grupos de vertebrados", "difficulty": 2,
        "statement": "¿A qué grupo de vertebrados pertenecen las ranas y los sapos?",
        "answer": "Anfibios",
        "options": ["Anfibios", "Reptiles", "Peces", "Mamíferos"],
    },
    {
        "slug": "naturais", "unit": "Ecosistemas", "topic": "cadenas tróficas", "difficulty": 3,
        "statement": "En una cadena alimentaria, ¿qué seres vivos son los productores?",
        "answer": "Las plantas",
        "options": ["Las plantas", "Los leones", "Las bacterias", "Los zorros"],
    },
    {
        "slug": "naturais", "unit": "La materia", "topic": "cambios de estado", "difficulty": 3,
        "statement": "¿Cómo se llama el paso del agua líquida a vapor de agua al calentarse?",
        "answer": "Evaporación",
        "options": ["Evaporación", "Condensación", "Solidificación", "Fusión"],
    },
    {
        "slug": "naturais", "unit": "El cuerpo humano", "topic": "esqueleto", "difficulty": 3,
        "statement": "¿Cuántos huesos tiene aproximadamente el cuerpo humano adulto?",
        "answer": "206",
        "options": ["206", "50", "900", "12"],
    },
    {
        "slug": "naturais", "unit": "La energía", "topic": "fuentes renovables", "difficulty": 3,
        "statement": "¿Qué fuente de energía renovable aprovecha la fuerza del viento?",
        "answer": "Energía eólica",
        "options": ["Energía eólica", "Energía solar", "Energía nuclear", "Carbón"],
    },

    # ==================== CASTELLANO (10) ====================
    {
        "slug": "castellano", "unit": "Ortografía", "topic": "m antes de p y b", "difficulty": 1,
        "statement": "Completa la palabra con m o n: «ca___pana».",
        "answer": "m",
        "options": None,
    },
    {
        "slug": "castellano", "unit": "Gramática", "topic": "sílabas", "difficulty": 1,
        "statement": "¿Cuántas sílabas tiene la palabra «mariposa»?",
        "answer": "4",
        "options": ["4", "3", "5", "2"],
    },
    {
        "slug": "castellano", "unit": "Vocabulario", "topic": "antónimos", "difficulty": 1,
        "statement": "¿Cuál es el antónimo de «subir»?",
        "answer": "bajar",
        "options": ["bajar", "trepar", "saltar", "correr"],
    },
    {
        "slug": "castellano", "unit": "Vocabulario", "topic": "sinónimos", "difficulty": 2,
        "statement": "¿Cuál es un sinónimo de la palabra «veloz»?",
        "answer": "rápido",
        "options": ["rápido", "lento", "pesado", "antiguo"],
    },
    {
        "slug": "castellano", "unit": "Gramática", "topic": "clases de palabras", "difficulty": 2,
        "statement": "En la frase «El perro negro corre», ¿qué palabra es un adjetivo?",
        "answer": "negro",
        "options": ["negro", "perro", "corre", "El"],
    },
    {
        "slug": "castellano", "unit": "Gramática", "topic": "acentuación", "difficulty": 2,
        "statement": "Según su sílaba tónica, ¿qué tipo de palabra es «árbol»?",
        "answer": "Llana",
        "options": ["Llana", "Aguda", "Esdrújula", "Monosílaba"],
    },
    {
        "slug": "castellano", "unit": "Gramática", "topic": "prefijos", "difficulty": 2,
        "statement": "¿Qué prefijo añadimos a «posible» para formar su antónimo?",
        "answer": "im-",
        "options": ["im-", "re-", "sub-", "pre-"],
    },
    {
        "slug": "castellano", "unit": "Gramática", "topic": "verbos", "difficulty": 3,
        "statement": "¿En qué tiempo verbal está la forma «cantaré»?",
        "answer": "Futuro",
        "options": ["Futuro", "Pasado", "Presente", "Infinitivo"],
    },
    {
        "slug": "castellano", "unit": "Ortografía", "topic": "b y v", "difficulty": 3,
        "statement": "¿Qué palabra está escrita correctamente en castellano?",
        "answer": "estaba",
        "options": ["estaba", "estava", "hestaba", "estabha"],
    },
    {
        "slug": "castellano", "unit": "Gramática", "topic": "acentuación", "difficulty": 3,
        "statement": "¿Cuál de estas palabras es esdrújula y lleva tilde siempre?",
        "answer": "pájaro",
        "options": ["pájaro", "reloj", "mesa", "camión"],
    },

    # ==================== MATES (10) ====================
    {
        "slug": "mates", "unit": "Numeración", "topic": "valor posicional", "difficulty": 1,
        "statement": "¿Qué número se forma con 3 centenas, 4 decenas y 5 unidades?",
        "answer": "345",
        "options": None,
    },
    {
        "slug": "mates", "unit": "Cálculo", "topic": "doble", "difficulty": 1,
        "statement": "¿Cuál es el doble del número 18?",
        "answer": "36",
        "options": None,
    },
    {
        "slug": "mates", "unit": "Cálculo", "topic": "mitad", "difficulty": 1,
        "statement": "¿Cuál es la mitad de 48?",
        "answer": "24",
        "options": ["24", "22", "26", "14"],
    },
    {
        "slug": "mates", "unit": "Medida", "topic": "tiempo", "difficulty": 2,
        "statement": "¿Cuántos minutos hay en 2 horas?",
        "answer": "120",
        "options": None,
    },
    {
        "slug": "mates", "unit": "Medida", "topic": "longitud", "difficulty": 2,
        "statement": "¿Cuántos centímetros son 3 metros?",
        "answer": "300",
        "options": ["300", "30", "3000", "3"],
    },
    {
        "slug": "mates", "unit": "Geometría", "topic": "polígonos", "difficulty": 2,
        "statement": "¿Cuántos lados tiene un hexágono?",
        "answer": "6",
        "options": ["6", "5", "7", "8"],
    },
    {
        "slug": "mates", "unit": "Operaciones", "topic": "multiplicación", "difficulty": 2,
        "statement": "En una caja hay 8 lápices. ¿Cuántos lápices habrá en 7 cajas iguales?",
        "answer": "56",
        "options": None,
    },
    {
        "slug": "mates", "unit": "Operaciones", "topic": "división", "difficulty": 3,
        "statement": "Si repartimos 72 caramelos en 8 bolsas iguales, ¿cuántos caramelos van en cada bolsa?",
        "answer": "9",
        "options": None,
    },
    {
        "slug": "mates", "unit": "Geometría", "topic": "perímetro", "difficulty": 3,
        "statement": "¿Cuál es el perímetro de un cuadrado cuyo lado mide 9 cm?",
        "answer": "36 cm",
        "options": ["36 cm", "18 cm", "81 cm", "27 cm"],
    },
    {
        "slug": "mates", "unit": "Fracciones", "topic": "concepto de fracción", "difficulty": 3,
        "statement": "Si divides una pizza en 4 trozos iguales y te comes 1 trozo, ¿qué fracción representa lo que comiste?",
        "answer": "1/4",
        "options": ["1/4", "4/1", "1/3", "3/4"],
    },
]

LANG_BY_SLUG = {
    "galego": "gl-ES",
    "ingles": "en-GB",
}


def validate_item(ex):
    st = ex["statement"].strip()
    ans = ex["answer"].strip()
    assert len(st) >= 15, f"Statement too short: {st}"
    assert 1 <= len(ans) <= 60, f"Answer invalid len: {ans}"
    assert re.search(r"[0-9a-záéíóúñü]", ans, re.I), f"Answer has no letter/digit: {ans}"
    assert ex["difficulty"] in (1, 2, 3), f"Invalid difficulty: {ex['difficulty']}"
    opts = ex["options"]
    if opts is not None:
        assert isinstance(opts, list) and len(opts) in (3, 4), f"Invalid options count: {opts}"
        assert ans in opts, f"Answer '{ans}' not in options {opts}"
        assert len(set(opts)) == len(opts), f"Duplicate options: {opts}"


def main():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")

    # Garantir materia 'naturais'
    con.execute(
        "INSERT OR IGNORE INTO subjects(slug, name, drive_id) VALUES(?, ?, NULL)",
        ("naturais", "Naturais"),
    )
    con.commit()

    subjects = {
        r["slug"]: r["id"]
        for r in con.execute("SELECT id, slug FROM subjects").fetchall()
    }

    inserted = 0
    skipped = 0
    for ex in EXERCISES:
        validate_item(ex)
        sid = subjects[ex["slug"]]
        st = ex["statement"].strip()
        existing = con.execute(
            "SELECT id FROM exercises WHERE subject_id=? AND statement=?",
            (sid, st),
        ).fetchone()
        if existing:
            skipped += 1
            continue

        opts = ex["options"]
        kind = "escolha_multipla" if opts is not None else "resposta_curta"
        opts_json = json.dumps(opts, ensure_ascii=False) if opts is not None else None
        lang = LANG_BY_SLUG.get(ex["slug"], "es-ES")

        con.execute(
            """INSERT INTO exercises
               (subject_id, page_id, unit, topic, kind, statement, answer, options, difficulty, lang, source, created_at)
               VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, 'gerado', ?)""",
            (
                sid,
                ex["unit"],
                ex["topic"],
                kind,
                st,
                ex["answer"].strip(),
                opts_json,
                ex["difficulty"],
                lang,
                NOW(),
            ),
        )
        inserted += 1

    con.commit()
    print(f"seed_exercises: {inserted} inseridos, {skipped} já existentes (total spec: {len(EXERCISES)})")


if __name__ == "__main__":
    main()
