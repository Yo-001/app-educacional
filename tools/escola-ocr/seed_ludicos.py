#!/usr/bin/env python3
"""Semeadura idempotente da matriz de 180 exercicios ludicos (3o/4o Primaria).

6 materias x 30 exercicios (10 dif 1, 10 dif 2, 10 dif 3) distribuidos entre
6 mecanicas: parejas, ordenar, dis, escri, vf, escolha_multipla (opts).
"""
import json
import os
import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(ROOT, "escola.db")
NOW = lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

SUBJECT_META = [
    ("mates", "Mates"),
    ("castellano", "Castellano"),
    ("galego", "Galego"),
    ("ingles", "Inglês"),
    ("naturais", "Naturais"),
    ("sociais", "Sociais"),
]

LANG_BY_SLUG = {
    "mates": "es-ES",
    "castellano": "es-ES",
    "galego": "es-ES",
    "naturais": "es-ES",
    "sociais": "es-ES",
    "ingles": "en-US",
}


def parejas(slug, dif, unit, topic, statement, pairs):
    return {
        "slug": slug,
        "difficulty": dif,
        "unit": unit,
        "topic": topic,
        "kind": "parejas",
        "statement": statement,
        "answer": "-".join(p[0] for p in pairs),
        "options": pairs,
    }


def ordenar(slug, dif, unit, topic, statement, steps):
    return {
        "slug": slug,
        "difficulty": dif,
        "unit": unit,
        "topic": topic,
        "kind": "ordenar",
        "statement": statement,
        "answer": " → ".join(steps),
        "options": steps,
    }


def dis(slug, dif, unit, topic, statement, answer):
    return {
        "slug": slug,
        "difficulty": dif,
        "unit": unit,
        "topic": topic,
        "kind": "dis",
        "statement": statement,
        "answer": answer,
        "options": None,
    }


def escri(slug, dif, unit, topic, statement, answer):
    return {
        "slug": slug,
        "difficulty": dif,
        "unit": unit,
        "topic": topic,
        "kind": "escri",
        "statement": statement,
        "answer": answer,
        "options": None,
    }


def vf(slug, dif, unit, topic, statement, answer, opts):
    return {
        "slug": slug,
        "difficulty": dif,
        "unit": unit,
        "topic": topic,
        "kind": "vf",
        "statement": statement,
        "answer": answer,
        "options": opts,
    }


def mc(slug, dif, unit, topic, statement, answer, opts):
    return {
        "slug": slug,
        "difficulty": dif,
        "unit": unit,
        "topic": topic,
        "kind": "escolha_multipla",
        "statement": statement,
        "answer": answer,
        "options": opts,
    }


VF_ES = ["Verdadero", "Falso"]
VF_GL = ["Verdadeiro", "Falso"]
VF_EN = ["True", "False"]

EXERCISES = [
    # ==================== MATES (30 - Castellano) ====================
    # dif 1 (10): 2 parejas, 2 ordenar, 1 dis, 2 escri, 2 vf, 1 mc
    parejas("mates", 1, "Cálculo", "sumas básicas",
            "Une cada suma sencilla con su resultado correcto:",
            [["7 + 5", "12"], ["9 + 6", "15"], ["8 + 8", "16"], ["4 + 9", "13"]]),
    parejas("mates", 1, "Numeración", "decenas",
            "Empareja cada número con su descomposición en decenas y unidades:",
            [["34", "3D + 4U"], ["52", "5D + 2U"], ["78", "7D + 8U"], ["91", "9D + 1U"]]),
    ordenar("mates", 1, "Numeración", "ordenar números",
            "Toca estos números de menor a mayor:",
            ["148", "235", "419", "602"]),
    ordenar("mates", 1, "Medida", "unidades de tiempo",
            "Ordena estas unidades de tiempo de la más corta a la más larga:",
            ["Segundo", "Minuto", "Hora", "Día"]),
    dis("mates", 1, "Cálculo", "tablas básicas",
        "Di en voz alta cuánto es 6 por 4.", "24"),
    escri("mates", 1, "Cálculo", "restas",
          "Escribe el resultado de restar 50 menos 18.", "32"),
    escri("mates", 1, "Numeración", "anterior y posterior",
          "Escribe el número posterior a 399.", "400"),
    vf("mates", 1, "Geometría", "triángulos",
       "¿Es cierto que un triángulo tiene exactamente tres lados?", "Verdadero", VF_ES),
    vf("mates", 1, "Numeración", "pares e impares",
       "El número 47 es un número par.", "Falso", VF_ES),
    mc("mates", 1, "Medida", "dinero",
       "Si tienes dos monedas de 50 céntimos, ¿cuánto dinero tienes en total?",
       "1 euro", ["1 euro", "2 euros", "50 céntimos", "10 euros"]),

    # dif 2 (10): 2 parejas, 1 ordenar, 2 dis, 2 escri, 1 vf, 2 mc
    parejas("mates", 2, "Cálculo", "tablas de multiplicar",
            "Une cada multiplicación con su producto:",
            [["6 × 7", "42"], ["8 × 5", "40"], ["9 × 4", "36"], ["7 × 8", "56"]]),
    parejas("mates", 2, "Geometría", "polígonos",
            "Empareja cada polígono con su número de lados:",
            [["Triángulo", "3 lados"], ["Cuadrado", "4 lados"], ["Pentágono", "5 lados"], ["Hexágono", "6 lados"]]),
    ordenar("mates", 2, "Medida", "longitudes",
            "Ordena estas longitudes de menor a mayor:",
            ["50 cm", "1 m", "150 cm", "2 m"]),
    dis("mates", 2, "Cálculo", "doble",
        "Di en voz alta el doble de 35.", "70"),
    dis("mates", 2, "Cálculo", "divisiones exactas",
        "Di en voz alta cuánto es 45 dividido entre 5.", "9"),
    escri("mates", 2, "Cálculo", "multiplicaciones",
          "Calcula y escribe el resultado de 23 × 4.", "92"),
    escri("mates", 2, "Problemas", "compras",
          "Un álbum cuesta 14 euros y compras 2 iguales. ¿Cuántos euros pagas?", "28"),
    vf("mates", 2, "Medida", "reloj",
       "En un reloj analógico, media hora equivale a 30 minutos.", "Verdadero", VF_ES),
    mc("mates", 2, "Numeración", "valor posicional",
       "¿Qué valor tiene la cifra 6 en el número 4.620?",
       "600", ["600", "60", "6.000", "6"]),
    mc("mates", 2, "Geometría", "ángulos",
       "¿Cómo se llama el ángulo que mide exactamente 90 grados?",
       "Ángulo recto", ["Ángulo recto", "Ángulo agudo", "Ángulo obtuso", "Ángulo llano"]),

    # dif 3 (10): 1 parejas, 2 ordenar, 2 dis, 1 escri, 2 vf, 2 mc
    parejas("mates", 3, "Fracciones", "lectura de fracciones",
            "Empareja cada fracción con su lectura correcta:",
            [["1/2", "Un medio"], ["1/3", "Un tercio"], ["3/4", "Tres cuartos"], ["2/5", "Dos quintos"]]),
    ordenar("mates", 3, "Fracciones", "ordenar fracciones",
            "Ordena estas fracciones de menor a mayor:",
            ["1/8", "3/8", "5/8", "7/8"]),
    ordenar("mates", 3, "Problemas", "pasos de un problema",
            "Ordena los pasos para resolver un problema matemático:",
            ["Leer el enunciado", "Anotar los datos", "Elegir la operación", "Comprobar el resultado"]),
    dis("mates", 3, "Geometría", "perímetro",
        "Di en voz alta el perímetro de un triángulo equilátero de 12 cm de lado.", "36"),
    dis("mates", 3, "Cálculo", "divisiones",
        "Di en voz alta cuánto es 72 dividido entre 8.", "9"),
    escri("mates", 3, "Medida", "capacidad",
          "¿Cuántos cuartos de litro hay en 3 litros? Escribe el número.", "12"),
    vf("mates", 3, "Geometría", "rectas",
       "Dos rectas paralelas se cortan siempre en un punto.", "Falso", VF_ES),
    vf("mates", 3, "Cálculo", "propiedad conmutativa",
       "En una multiplicación, cambiar el orden de los factores no altera el producto.", "Verdadero", VF_ES),
    mc("mates", 3, "Problemas", "divisiones con resto",
       "Repartimos 29 caramelos en bolsas de 4. ¿Cuántos caramelos sobran sin bolsa?",
       "1", ["1", "2", "3", "7"]),
    mc("mates", 3, "Medida", "masa",
       "¿Cuántos gramos son 2 kilogramos y medio?",
       "2.500 g", ["2.500 g", "250 g", "2.050 g", "5.000 g"]),

    # ==================== CASTELLANO (30 - Castellano) ====================
    # dif 1 (10): 2 parejas, 2 ordenar, 1 dis, 2 escri, 2 vf, 1 mc
    parejas("castellano", 1, "Vocabulario", "antónimos",
            "Une cada palabra con su antónimo:",
            [["Alto", "Bajo"], ["Rápido", "Lento"], ["Día", "Noche"], ["Lleno", "Vacío"]]),
    parejas("castellano", 1, "Gramática", "artículos",
            "Empareja cada sustantivo con su artículo determinado:",
            [["casa", "la"], ["árbol", "el"], ["flores", "las"], ["libros", "los"]]),
    ordenar("castellano", 1, "Vocabulario", "orden alfabético",
            "Ordena estas palabras alfabéticamente:",
            ["Avión", "Barco", "Casa", "Dado"]),
    ordenar("castellano", 1, "Gramática", "construir oración",
            "Ordena las palabras para formar una oración con sentido:",
            ["El perro", "corre", "por el", "parque"]),
    dis("castellano", 1, "Vocabulario", "sinónimos",
        "Di en voz alta un sinónimo de la palabra «contento».", "alegre"),
    escri("castellano", 1, "Gramática", "plurales",
          "Escribe el plural de la palabra «pez».", "peces"),
    escri("castellano", 1, "Vocabulario", "familias de palabras",
          "Escribe la palabra primitiva de la familia: «panadero, panadería, empanada».", "pan"),
    vf("castellano", 1, "Ortografía", "mayúsculas",
       "Los nombres propios de personas y ciudades se escriben siempre con mayúscula inicial.", "Verdadero", VF_ES),
    vf("castellano", 1, "Fonética", "vocales",
       "La palabra «sol» tiene dos sílabas.", "Falso", VF_ES),
    mc("castellano", 1, "Gramática", "sustantivos",
       "¿Cuál de estas palabras es un sustantivo propio?",
       "Madrid", ["Madrid", "ciudad", "montaña", "río"]),

    # dif 2 (10): 2 parejas, 1 ordenar, 2 dis, 2 escri, 1 vf, 2 mc
    parejas("castellano", 2, "Vocabulario", "aumentativos y diminutivos",
            "Une cada palabra con su diminutivo:",
            [["Perro", "Perrito"], ["Flor", "Florecita"], ["Mesa", "Mesita"], ["Árbol", "Arbolito"]]),
    parejas("castellano", 2, "Gramática", "clases de palabras",
            "Empareja cada palabra con su categoría gramatical:",
            [["Saltar", "Verbo"], ["Bonito", "Adjetivo"], ["Nosotros", "Pronombre"], ["Mochila", "Sustantivo"]]),
    ordenar("castellano", 2, "Comunicación", "partes de una carta",
            "Ordena las partes de una carta de principio a fin:",
            ["Fecha y lugar", "Saludo", "Cuerpo del texto", "Despedida y firma"]),
    dis("castellano", 2, "Gramática", "tiempos verbales",
        "Di en voz alta el tiempo verbal (pasado, presente o futuro) de «mañana estudiaré».", "futuro"),
    dis("castellano", 2, "Ortografía", "acentuación",
        "Di en voz alta si la palabra «canción» es aguda, llana o esdrújula.", "aguda"),
    escri("castellano", 2, "Ortografía", "m antes de p y b",
          "Completa correctamente la palabra «ca__pana» escribiendo la palabra entera.", "campana"),
    escri("castellano", 2, "Vocabulario", "prefijos",
          "Añade el prefijo «des-» a «ordenar» y escribe la nueva palabra.", "desordenar"),
    vf("castellano", 2, "Ortografía", "reglas de h",
       "Las palabras que empiezan por «hie-» o «hue-» se escriben con h.", "Verdadero", VF_ES),
    mc("castellano", 2, "Gramática", "adjetivos",
       "En la frase «La gata blanca duerme», ¿qué palabra es el adjetivo?",
       "blanca", ["blanca", "gata", "duerme", "la"]),
    mc("castellano", 2, "Ortografía", "r y rr",
       "¿Qué palabra está escrita correctamente?",
       "alrededor", ["alrededor", "alrrededor", "harededor", "alrededorr"]),

    # dif 3 (10): 1 parejas, 2 ordenar, 2 dis, 1 escri, 2 vf, 2 mc
    parejas("castellano", 3, "Ortografía", "acentuación",
            "Une cada palabra con su tipo según la sílaba tónica:",
            [["Reloj", "Aguda"], ["Árbol", "Llana"], ["Brújula", "Esdrújula"], ["Sofá", "Aguda con tilde"]]),
    ordenar("castellano", 3, "Literatura", "estructura narrativa",
            "Ordena las partes de un cuento clásico:",
            ["Introducción", "Nudo o conflicto", "Clímax", "Desenlace"]),
    ordenar("castellano", 3, "Vocabulario", "orden alfabético avanzado",
            "Ordena alfabéticamente estas palabras que empiezan igual:",
            ["Casa", "Cascada", "Casco", "Castillo"]),
    dis("castellano", 3, "Gramática", "sujeto",
        "En «Los niños juegan en el patio», di en voz alta cuál es el verbo.", "juegan"),
    dis("castellano", 3, "Vocabulario", "palabras compuestas",
        "Di en voz alta la palabra compuesta formada por «para» y «aguas».", "paraguas"),
    escri("castellano", 3, "Gramática", "gentilicios",
          "Escribe el gentilicio de una persona nacida en Galicia (masculino singular).", "gallego"),
    vf("castellano", 3, "Ortografía", "esdrújulas",
       "Todas las palabras esdrújulas en castellano llevan tilde.", "Verdadero", VF_ES),
    vf("castellano", 3, "Gramática", "pronombres",
       "La palabra «vosotros» es un pronombre personal de primera persona.", "Falso", VF_ES),
    mc("castellano", 3, "Vocabulario", "palabras polisémicas",
       "¿Cuál de estas palabras es polisémica porque tiene varios significados (instrumento, animal, parte del cuerpo)?",
       "gato", ["gato", "hipopótamo", "martillo", "semáforo"]),
    mc("castellano", 3, "Ortografía", "b y v",
       "¿Qué forma verbal está escrita correctamente?",
       "caminaba", ["caminaba", "caminava", "kaminaba", "camynaba"]),

    # ==================== GALEGO (30 - Galego) ====================
    # dif 1 (10): 2 parejas, 2 ordenar, 1 dis, 2 escri, 2 vf, 1 mc
    parejas("galego", 1, "Vocabulario", "cores en galego",
            "Une cada obxecto coa súa cor habitual en galego:",
            [["Limón", "Amarelo"], ["Herba", "Verde"], ["Ceo", "Azul"], ["Neve", "Branco"]]),
    parejas("galego", 1, "Vocabulario", "familia",
            "Emparella cada membro da familia en galego co seu par:",
            [["Pai", "Nai"], ["Avó", "Avoa"], ["Irmán", "Irmá"], ["Tío", "Tía"]]),
    ordenar("galego", 1, "Vocabulario", "estacións do ano",
            "Ordena as catro estacións do ano comezando pola primavera:",
            ["Primavera", "Verán", "Outono", "Inverno"]),
    ordenar("galego", 1, "Vocabulario", "días da semana",
            "Toca en orde os catro primeiros días laborables da semana:",
            ["Luns", "Martes", "Mércores", "Xoves"]),
    dis("galego", 1, "Vocabulario", "animais",
        "Di en voz alta como se chama en galego o animal que fai «miau».", "gato"),
    escri("galego", 1, "Vocabulario", "saúdos",
          "Escribe como se di en galego «Buenos días».", "Bos días"),
    escri("galego", 1, "Gramática", "artigos",
          "Escribe o artigo feminino plural en galego para acompañar a «estrelas».", "as"),
    vf("galego", 1, "Vocabulario", "estacións",
       "En galego, a palabra «outono» refírese á estación na que caen as follas.", "Verdadeiro", VF_GL),
    vf("galego", 1, "Ortografía", "alfabeto galego",
       "A letra «ñ» forma parte do alfabeto galego.", "Verdadeiro", VF_GL),
    mc("galego", 1, "Vocabulario", "escola",
       "Como se chama en galego o obxecto que usamos para borrar o lapis?",
       "goma", ["goma", "caderno", "tesoiras", "regra"]),

    # dif 2 (10): 2 parejas, 1 ordenar, 2 dis, 2 escri, 1 vf, 2 mc
    parejas("galego", 2, "Gramática", "contraccións",
            "Une cada suma de preposición e artigo coa súa contracción galega:",
            [["de + o", "do"], ["en + a", "na"], ["con + o", "co"], ["por + a", "pola"]]),
    parejas("galego", 2, "Vocabulario", "antónimos",
            "Emparella cada palabra galega co seu antónimo:",
            [["Grande", "Pequeno"], ["Novo", "Vello"], ["Claro", "Escuro"], ["Doce", "Amargo"]]),
    ordenar("galego", 2, "Vocabulario", "orde alfabética",
            "Ordena alfabeticamente estas palabras galegas:",
            ["Auga", "Bote", "Camiño", "Dente"]),
    dis("galego", 2, "Vocabulario", "natureza",
        "Di en voz alta como se chama en galego a árbore que dá mazás.", "maceira"),
    dis("galego", 2, "Gramática", "números",
        "Di en voz alta como se di o número 12 en galego.", "doce"),
    escri("galego", 2, "Ortografía", "o x en galego",
          "Escribe en galego o nome do líquido branco que sae das vacas.", "leite"),
    escri("galego", 2, "Gramática", "plurais en -ns",
          "Escribe o plural correcto en galego da palabra «irmán».", "irmáns"),
    vf("galego", 2, "Gramática", "xénero",
       "En galego, a palabra «ponte» é de xénero feminino («a ponte»).", "Verdadeiro", VF_GL),
    mc("galego", 2, "Vocabulario", "oficios",
       "Quen traballa no mar pescando peixes e marisco?",
       "mariñeiro", ["mariñeiro", "panadeiro", "carpinteiro", "xardineiro"]),
    mc("galego", 2, "Ortografía", "dígrafos",
       "Que palabra galega está ben escrita co dígrafo «nh»?",
       "unha", ["unha", "uña", "unlla", "una"]),

    # dif 3 (10): 1 parejas, 2 ordenar, 2 dis, 1 escri, 2 vf, 2 mc
    parejas("galego", 3, "Vocabulario", "árbores e froitos",
            "Une cada árbore galega co seu froito:",
            [["Castiñeiro", "Castaña"], ["Carballo", "Landra"], ["Cerqueiro", "Cereixa"], ["Nogueira", "Noz"]]),
    ordenar("galego", 3, "Gramática", "construír oración",
            "Ordena os fragmentos para formar unha oración correcta en galego:",
            ["Os rapaces", "leron un", "conto moi", "divertido"]),
    ordenar("galego", 3, "Literatura", "meses do verán",
            "Ordena os meses desde xuño ata setembro:",
            ["Xuño", "Xullo", "Agosto", "Setembro"]),
    dis("galego", 3, "Vocabulario", "meteoroloxía",
        "Di en voz alta como se chama en galego a choiva moi fina e suave.", "orballo"),
    dis("galego", 3, "Gramática", "verbos",
        "Di en voz alta o infinitivo do verbo na frase «mañá cantaremos unha canción».", "cantar"),
    escri("galego", 3, "Ortografía", "til diacrítico",
          "Escribe con til diacrítico a palabra galega para unha esfera ou pelota pequena («bóla»).",
          "bóla"),
    vf("galego", 3, "Ortografía", "uso do x",
       "En galego, a palabra «xente» escríbese con x e non con j.", "Verdadeiro", VF_GL),
    vf("galego", 3, "Gramática", "pronomes",
       "En galego correcto dise «eu dixen» e nunca «eu dicín».", "Verdadeiro", VF_GL),
    mc("galego", 3, "Vocabulario", "expresións galegas",
       "Que significa a expresión galega «estar nas nubes»?",
       "Estar distraído", ["Estar distraído", "Voar en avión", "Ter moito frío", "Chover forte"]),
    mc("galego", 3, "Ortografía", "plurais en -is",
       "Cal é o plural correcto da palabra galega «animal»?",
       "animais", ["animais", "animales", "animals", "animás"]),

    # ==================== INGLES (30 - Inglés) ====================
    # dif 1 (10): 2 parejas, 2 ordenar, 1 dis, 2 escri, 2 vf, 1 mc
    parejas("ingles", 1, "Vocabulary", "colours",
            "Match each English colour with its Spanish meaning:",
            [["Red", "Rojo"], ["Blue", "Azul"], ["Green", "Verde"], ["Yellow", "Amarillo"]]),
    parejas("ingles", 1, "Vocabulary", "animals",
            "Match each English animal with its Spanish translation:",
            [["Dog", "Perro"], ["Cat", "Gato"], ["Bird", "Pájaro"], ["Fish", "Pez"]]),
    ordenar("ingles", 1, "Vocabulary", "days of the week",
            "Tap the days of the week in order starting with Monday:",
            ["Monday", "Tuesday", "Wednesday", "Thursday"]),
    ordenar("ingles", 1, "Vocabulary", "numbers",
            "Order these English numbers from smallest to largest:",
            ["Two", "Five", "Eight", "Ten"]),
    dis("ingles", 1, "Vocabulary", "greetings",
        "Say aloud the English word for «manzana».", "apple"),
    escri("ingles", 1, "Vocabulary", "school",
          "Write in English the word for «libro».", "book"),
    escri("ingles", 1, "Grammar", "to be",
          "Complete the sentence with one word: «I ___ nine years old.»", "am"),
    vf("ingles", 1, "Vocabulary", "body parts",
       "In English, «nose» means «nariz».", "True", VF_EN),
    vf("ingles", 1, "Vocabulary", "weather",
       "In English, «sunny» means «lluvioso».", "False", VF_EN),
    mc("ingles", 1, "Vocabulary", "family",
       "How do you say «hermana» in English?",
       "sister", ["sister", "brother", "mother", "aunt"]),

    # dif 2 (10): 2 parejas, 1 ordenar, 2 dis, 2 escri, 1 vf, 2 mc
    parejas("ingles", 2, "Vocabulary", "house rooms",
            "Match each room of the house with what it means:",
            [["Kitchen", "Cocina"], ["Bedroom", "Dormitorio"], ["Bathroom", "Baño"], ["Garden", "Jardín"]]),
    parejas("ingles", 2, "Vocabulary", "opposites",
            "Match each English adjective with its opposite:",
            [["Big", "Small"], ["Hot", "Cold"], ["Fast", "Slow"], ["Happy", "Sad"]]),
    ordenar("ingles", 2, "Vocabulary", "months",
            "Order these months from January to April:",
            ["January", "February", "March", "April"]),
    dis("ingles", 2, "Vocabulary", "seasons",
        "Say aloud the English season when it is very cold and snows.", "winter"),
    dis("ingles", 2, "Vocabulary", "animals",
        "Say aloud the name of the big grey animal with a long trunk in English.", "elephant"),
    escri("ingles", 2, "Grammar", "plurals",
          "Write the plural of «child» in English.", "children"),
    escri("ingles", 2, "Vocabulary", "clothes",
          "Write in English the word for «zapatos».", "shoes"),
    vf("ingles", 2, "Grammar", "articles",
       "We say «an elephant» because «elephant» starts with a vowel sound.", "True", VF_EN),
    mc("ingles", 2, "Grammar", "present simple",
       "Choose the correct option: «Tom ___ football every Saturday.»",
       "plays", ["plays", "play", "playing", "is play"]),
    mc("ingles", 2, "Vocabulary", "telling time",
       "What does «half past three» mean?",
       "3:30", ["3:30", "3:15", "3:45", "3:00"]),

    # dif 3 (10): 1 parejas, 2 ordenar, 2 dis, 1 escri, 2 vf, 2 mc
    parejas("ingles", 3, "Grammar", "question words",
            "Match each English question word with its meaning:",
            [["Who", "Quién"], ["Where", "Dónde"], ["When", "Cuándo"], ["Why", "Por qué"]]),
    ordenar("ingles", 3, "Grammar", "sentence order",
            "Order the words to make a correct English sentence:",
            ["She", "always", "reads", "books"]),
    ordenar("ingles", 3, "Vocabulary", "daily routine",
            "Order these daily routine actions from morning to night:",
            ["Wake up", "Have breakfast", "Go to school", "Go to sleep"]),
    dis("ingles", 3, "Vocabulary", "places in town",
        "Say aloud the English place where you go to borrow books.", "library"),
    dis("ingles", 3, "Vocabulary", "weekends",
        "Say aloud the English day that comes after Friday.", "Saturday"),
    escri("ingles", 3, "Grammar", "past simple",
          "Write the past simple of the verb «go» in English.", "went"),
    vf("ingles", 3, "Grammar", "there is / there are",
       "We use «There are» for plural nouns, like «There are three cats».", "True", VF_EN),
    vf("ingles", 3, "Grammar", "possessives",
       "The word «their» is used to talk about something belonging to «they».", "True", VF_EN),
    mc("ingles", 3, "Grammar", "comparatives",
       "Choose the right comparative: «A cheetah is ___ than a turtle.»",
       "faster", ["faster", "fastest", "more fast", "fast"]),
    mc("ingles", 3, "Grammar", "prepositions",
       "Complete the sentence: «The cat is hiding ___ the table.»",
       "under", ["under", "between", "into", "through"]),

    # ==================== NATURAIS (30 - Galego) ====================
    # dif 1 (10): 2 parejas, 2 ordenar, 1 dis, 2 escri, 2 vf, 1 mc
    parejas("naturais", 1, "Os sentidos", "órganos dos sentidos",
            "Une cada sentido co órgano do corpo correspondente:",
            [["Vista", "Ollos"], ["Oído", "Orellas"], ["Olfacto", "Nariz"], ["Gusto", "Lingua"]]),
    parejas("naturais", 1, "Os animais", "desprazamento",
            "Emparella cada animal coa forma principal na que se despraza:",
            [["Aguia", "Voa"], ["Sardiña", "Nada"], ["Cabalo", "Corre"], ["Serpe", "Repta"]]),
    ordenar("naturais", 1, "As plantas", "ciclo da semente",
            "Ordena as etapas do crecemento dunha planta desde a semente:",
            ["Semente", "Raíz", "Talo", "Follas e flor"]),
    ordenar("naturais", 1, "O corpo humano", "etapas da vida",
            "Ordena as etapas da vida humana de menor a maior idade:",
            ["Infancia", "Adolescencia", "Idade adulta", "Vellez"]),
    dis("naturais", 1, "As plantas", "nutrición vexetal",
        "Di en voz alta que estrela dá a luz que necesitan as plantas para medrar.", "sol"),
    escri("naturais", 1, "Os seres vivos", "funcións vitais",
          "Escribe o nome da función vital pola que os seres vivos teñen crías.", "reprodución"),
    escri("naturais", 1, "A materia", "estados da auga",
          "Escribe como se chama a auga en estado sólido polo frío.", "xeo"),
    vf("naturais", 1, "Os seres vivos", "seres inertes",
       "Unha pedra é un ser vivo porque está na natureza.", "Falso", VF_GL),
    vf("naturais", 1, "Os animais", "vertebrados",
       "Os animais vertebrados teñen esqueleto interno con columna vertebral.", "Verdadeiro", VF_GL),
    mc("naturais", 1, "As plantas", "partes da planta",
       "Que parte da planta absorbe a auga e os sales minerais do solo?",
       "A raíz", ["A raíz", "A folla", "O pétalo", "O froito"]),

    # dif 2 (10): 2 parejas, 1 ordenar, 2 dis, 2 escri, 1 vf, 2 mc
    parejas("naturais", 2, "Os animais", "grupos de vertebrados",
            "Une cada animal co grupo de vertebrados ao que pertence:",
            [["Balea", "Mamífero"], ["Ra", "Anfibio"], ["Lagarto", "Réptil"], ["Troita", "Peixe"]]),
    parejas("naturais", 2, "O corpo humano", "aparellos",
            "Emparella cada aparello do corpo coa súa función:",
            [["Dixestivo", "Dixire alimentos"], ["Respiratorio", "Toma osíxeno"], ["Circulatorio", "Move o sangue"], ["Locomotor", "Permite o movemento"]]),
    ordenar("naturais", 2, "O medio ambiente", "cadea alimentaria",
            "Ordena esta cadea alimentaria desde o produtor ata o último consumidor:",
            ["Herba", "Coello", "Raposo", "Aguia"]),
    dis("naturais", 2, "As plantas", "fotosíntese",
        "Di en voz alta o nome do proceso polo que as plantas fabrican o seu alimento coa luz.", "fotosíntese"),
    dis("naturais", 2, "O corpo humano", "respiración",
        "Di en voz alta o nome dos dous órganos esponxosos cos que respiramos.", "pulmóns"),
    escri("naturais", 2, "Os animais", "alimentación",
          "Como se chaman os animais que só comen plantas? Escribe a palabra.", "herbívoros"),
    escri("naturais", 2, "As plantas", "pigmentos",
          "Escribe o nome da substancia verde das follas que capta a luz solar.", "clorofila"),
    vf("naturais", 2, "Os animais", "ovíparos",
       "As aves e a maioría dos réptiles son animais ovíparos porque nacen de ovos.", "Verdadeiro", VF_GL),
    mc("naturais", 2, "Os seres vivos", "cinco reinos",
       "A que reino pertencen os cogomelos e os lévedos?",
       "Fungos", ["Fungos", "Plantas", "Moneras", "Protistas"]),
    mc("naturais", 2, "Saúde", "alimentación saudable",
       "Cal destes alimentos pertence ao grupo das froitas e achega moitas vitaminas?",
       "laranxa", ["laranxa", "manteiga", "pan", "queixo"]),

    # dif 3 (10): 1 parejas, 2 ordenar, 2 dis, 1 escri, 2 vf, 2 mc
    parejas("naturais", 3, "A materia", "cambios de estado",
            "Une cada cambio de estado da auga coa súa descrición:",
            [["Fusión", "De sólido a líquido"], ["Evaporación", "De líquido a gas"], ["Solidificación", "De líquido a sólido"], ["Condensación", "De gas a líquido"]]),
    ordenar("naturais", 3, "A auga", "ciclo da auga",
            "Ordena as catro fases principais do ciclo da auga:",
            ["Evaporación", "Condensación", "Precipitación", "Retorno ao mar"]),
    ordenar("naturais", 3, "O corpo humano", "dixestión",
            "Ordena o percorrido dos alimentos polo tubo dixestivo:",
            ["Boca", "Esófago", "Estómago", "Intestinos"]),
    dis("naturais", 3, "As plantas", "gases da fotosíntese",
        "Di en voz alta o gas que liberan as plantas ao aire durante a fotosíntese.", "osíxeno"),
    dis("naturais", 3, "Os seres vivos", "célula",
        "Di en voz alta como se chama a unidade máis pequena que forma todos os seres vivos.", "célula"),
    escri("naturais", 3, "Ecosistemas", "relacións",
          "Escribe como se chama o conxunto formado polos seres vivos e o medio físico onde viven.", "ecosistema"),
    vf("naturais", 3, "Os animais", "anfibios",
       "Os anfibios sofren metamorfose ao pasar de cágados acuáticos a adultos.", "Verdadeiro", VF_GL),
    vf("naturais", 3, "A enerxía", "enerxías renovables",
       "O carbón e o petróleo son fontes de enerxía renovables que nunca se esgotan.", "Falso", VF_GL),
    mc("naturais", 3, "As plantas", "partes da flor",
       "Cal é a parte feminina da flor onde se atopan os óvulos?",
       "O pistilo", ["O pistilo", "O estame", "O cáliz", "A corola"]),
    mc("naturais", 3, "A materia", "forzas e máquinas",
       "Cal destas opcións é unha máquina simple?",
       "polea", ["polea", "ordenador", "lavadora", "automóbil"]),

    # ==================== SOCIAIS (30 - Galego) ====================
    # dif 1 (10): 2 parejas, 2 ordenar, 1 dis, 2 escri, 2 vf, 1 mc
    parejas("sociais", 1, "Xeografía de Galicia", "provincias galegas",
            "Une cada provincia galega coa súa cidade capital:",
            [["A Coruña", "A Coruña"], ["Lugo", "Lugo"], ["Ourense", "Ourense"], ["Pontevedra", "Pontevedra"]]),
    parejas("sociais", 1, "O Universo", "astros",
            "Emparella cada astro coa súa característica principal:",
            [["Sol", "Estrela central"], ["Terra", "Planeta onde vivimos"], ["Lúa", "Satélite da Terra"], ["Marte", "Planeta vermello"]]),
    ordenar("sociais", 1, "O tempo", "medida do tempo",
            "Ordena estas etapas históricas da máis antiga á máis actual:",
            ["Prehistoria", "Idade Antiga", "Idade Media", "Idade Contemporánea"]),
    ordenar("sociais", 1, "Organización", "do pequeno ao grande",
            "Ordena estes lugares do máis pequeno ao máis grande:",
            ["A miña rúa", "O meu concello", "Galicia", "Europa"]),
    dis("sociais", 1, "Xeografía", "puntos cardinais",
        "Di en voz alta por que punto cardinal sae o Sol cada mañá.", "leste"),
    escri("sociais", 1, "Xeografía de Galicia", "capital",
          "Escribe o nome da capital de Galicia.", "Santiago de Compostela"),
    escri("sociais", 1, "O Universo", "movementos",
          "Cantos días tarda a Terra en dar unha volta completa arredor do Sol? Escribe só o número.", "365"),
    vf("sociais", 1, "O Planeta", "rotación",
       "O movemento de rotación da Terra sobre si mesma dá lugar ao día e á noite.", "Verdadeiro", VF_GL),
    vf("sociais", 1, "Xeografía", "continentes",
       "Europa é o continente onde se atopan Galicia e España.", "Verdadeiro", VF_GL),
    mc("sociais", 1, "Servizos", "seguridade viaria",
       "Que cor do semáforo indica aos peóns que poden cruzar a rúa?",
       "Verde", ["Verde", "Vermella", "Amarela", "Azul"]),

    # dif 2 (10): 2 parejas, 1 ordenar, 2 dis, 2 escri, 1 vf, 2 mc
    parejas("sociais", 2, "Paisaxe", "relevo",
            "Une cada forma do relevo coa súa definición:",
            [["Montaña", "Elevación do terreo"], ["Val", "Terreo entre montañas"], ["Illa", "Terra rodeada de mar"], ["Cabo", "Punta de terra no mar"]]),
    parejas("sociais", 2, "Economía", "sectores económicos",
            "Emparella cada traballo co sector económico ao que pertence:",
            [["Agricultor", "Sector primario"], ["Carpinteiro", "Sector secundario"], ["Mestra", "Sector terciario"], ["Pescador", "Sector primario"]]),
    ordenar("sociais", 2, "Augas", "curso dun río",
            "Ordena o percorrido dun río desde onde nace ata onde chega ao mar:",
            ["Nacemento", "Curso alto", "Curso medio", "Desembocadura"]),
    dis("sociais", 2, "Xeografía", "océano de Galicia",
        "Di en voz alta o nome do océano que baña a costa oeste de Galicia.", "Atlántico"),
    dis("sociais", 2, "O Universo", "fases da Lúa",
        "Di en voz alta como se chama a fase da Lúa na que a vemos completamente redonda.", "Lúa chea"),
    escri("sociais", 2, "Xeografía", "ríos de Galicia",
          "Escribe o nome do río máis longo de Galicia.", "Miño"),
    escri("sociais", 2, "Representación da Terra", "planos e mapas",
          "Como se chama a representación plana de toda a superficie da Terra?", "planisferio"),
    vf("sociais", 2, "Clima", "tempo e clima",
       "A veleta serve para indicar a dirección na que sopra o vento.", "Verdadeiro", VF_GL),
    mc("sociais", 2, "Prehistoria", "etapas",
       "Que gran descubrimento marcou o paso da Prehistoria á Idade Antiga?",
       "A escritura", ["A escritura", "O lume", "A roda", "A imprenta"]),
    mc("sociais", 2, "O Universo", "planetas",
       "Cal é o planeta do Sistema Solar máis próximo ao Sol?",
       "Mercurio", ["Mercurio", "Venus", "Xúpiter", "Saturno"]),

    # dif 3 (10): 1 parejas, 2 ordenar, 2 dis, 1 escri, 2 vf, 2 mc
    parejas("sociais", 3, "Historia", "idades da historia",
            "Une cada invento ou elemento coa etapa histórica na que apareceu:",
            [["Pinturas rupestres", "Prehistoria"], ["Acueduto romano", "Idade Antiga"], ["Castelo medieval", "Idade Media"], ["Máquina de vapor", "Idade Contemporánea"]]),
    ordenar("sociais", 3, "O Universo", "planetas interiores",
            "Ordena os catro planetas rochosos desde o máis próximo ao Sol:",
            ["Mercurio", "Venus", "Terra", "Marte"]),
    ordenar("sociais", 3, "Poboación", "organización territorial",
            "Ordena de menor a maior nivel administrativo en España:",
            ["Concello", "Provincia", "Comunidade Autónoma", "Estado"]),
    dis("sociais", 3, "Xeografía", "límites de Galicia",
        "Di en voz alta o nome do mar que baña o norte de Galicia.", "Cantábrico"),
    dis("sociais", 3, "Clima", "instrumentos",
        "Di en voz alta o nome do instrumento que mide a cantidade de chuvia que cae.", "pluviómetro"),
    escri("sociais", 3, "Xeografía mundial", "océanos",
          "Escribe o nome do océano máis grande da Terra.", "Pacífico"),
    vf("sociais", 3, "Historia", "Idade Media",
       "Na Idade Media construíronse moitos castelos e mosteiros.", "Verdadeiro", VF_GL),
    vf("sociais", 3, "O Planeta", "paralelos",
       "O ecuador é a liña imaxinaria que divide a Terra en hemisferio norte e hemisferio sur.", "Verdadeiro", VF_GL),
    mc("sociais", 3, "Sociedade", "institucións",
       "Que institución goberna un concello xunto coas concelleiras e concelleiros?",
       "O alcalde ou alcaldesa", ["O alcalde ou alcaldesa", "O presidente do Goberno", "O xuíz de paz", "O director do colexio"]),
    mc("sociais", 3, "Clima", "capas da Terra",
       "Como se chama a capa de aire que rodea a Terra?",
       "Atmosfera", ["Atmosfera", "Hidrosfera", "Xeosfera", "Litosfera"]),
]


def validate_matrix():
    assert len(EXERCISES) == 180, f"Expected 180 exercises, got {len(EXERCISES)}"
    by_subj = Counter(e["slug"] for e in EXERCISES)
    by_kind = Counter(e["kind"] for e in EXERCISES)
    by_subj_dif = Counter((e["slug"], e["difficulty"]) for e in EXERCISES)
    by_subj_kind = Counter((e["slug"], e["kind"]) for e in EXERCISES)

    for slug, _ in SUBJECT_META:
        assert by_subj[slug] == 30, f"{slug}: expected 30, got {by_subj[slug]}"
        for d in (1, 2, 3):
            assert by_subj_dif[(slug, d)] == 10, f"{slug} dif {d}: expected 10, got {by_subj_dif[(slug, d)]}"
        for k in ("parejas", "ordenar", "dis", "escri", "vf", "escolha_multipla"):
            assert by_subj_kind[(slug, k)] == 5, f"{slug} kind {k}: expected 5, got {by_subj_kind[(slug, k)]}"
    assert sum(by_kind.values()) == 180

    seen = set()
    for ex in EXERCISES:
        st = ex["statement"].strip()
        ans = ex["answer"].strip()
        key = (ex["slug"], st)
        assert key not in seen, f"Duplicate statement: {key}"
        seen.add(key)
        assert len(st) >= 15, f"Short statement: {st}"
        assert ex["difficulty"] in (1, 2, 3)

        k = ex["kind"]
        opts = ex["options"]
        if k == "parejas":
            assert isinstance(opts, list) and len(opts) == 4
            for p in opts:
                assert isinstance(p, list) and len(p) == 2 and p[0].strip() and p[1].strip()
        elif k == "ordenar":
            assert isinstance(opts, list) and len(opts) == 4 and len(set(opts)) == 4
        elif k == "vf":
            assert isinstance(opts, list) and len(opts) == 2 and ans in opts
        elif k == "escolha_multipla":
            assert isinstance(opts, list) and len(opts) == 4 and len(set(opts)) == 4 and ans in opts
            assert 1 <= len(ans) <= 60
        elif k in ("dis", "escri"):
            assert opts is None
            assert 1 <= len(ans) <= 60 and re.search(r"[0-9a-záéíóúñü]", ans, re.I)


def main():
    validate_matrix()
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")

    for slug, name in SUBJECT_META:
        con.execute(
            "INSERT OR IGNORE INTO subjects(slug, name, drive_id) VALUES(?, ?, NULL)",
            (slug, name),
        )
    con.commit()

    subjects = {
        r["slug"]: r["id"]
        for r in con.execute("SELECT id, slug FROM subjects").fetchall()
    }

    inserted = 0
    skipped = 0
    for ex in EXERCISES:
        sid = subjects[ex["slug"]]
        st = ex["statement"].strip()
        existing = con.execute(
            "SELECT id FROM exercises WHERE subject_id=? AND statement=?",
            (sid, st),
        ).fetchone()
        if existing:
            skipped += 1
            continue

        opts_json = (
            json.dumps(ex["options"], ensure_ascii=False)
            if ex["options"] is not None
            else None
        )
        lang = LANG_BY_SLUG[ex["slug"]]

        con.execute(
            """INSERT INTO exercises
               (subject_id, page_id, unit, topic, kind, statement, answer, options, difficulty, lang, source, created_at)
               VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, 'gerado', ?)""",
            (
                sid,
                ex["unit"],
                ex["topic"],
                ex["kind"],
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
    print(f"seed_ludicos: {inserted} inseridos, {skipped} já existentes (matriz: {len(EXERCISES)})")


if __name__ == "__main__":
    main()
