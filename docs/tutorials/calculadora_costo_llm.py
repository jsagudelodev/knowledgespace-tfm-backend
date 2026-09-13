#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CALCULADORA DE COSTO DE SOLICITUD AL LLM

Herramienta para:
1. Ver los precios de cada modelo de OpenAI
2. Calcular el costo exacto de una solicitud
3. Simular múltiples consultas
4. Entender la estructura de costos

Uso:
  python calculadora_costo_llm.py
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Tabla de precios de OpenAI (USD por 1K tokens)
PRICING = {
    "gpt-4o": {
        "input": 0.005,
        "output": 0.015,
    },
    "gpt-4o-mini": {
        "input": 0.00015,
        "output": 0.0006,
    },
    "gpt-4-turbo": {
        "input": 0.01,
        "output": 0.03,
    },
    "gpt-3.5-turbo": {
        "input": 0.0005,
        "output": 0.0015,
    },
    "text-embedding-3-small": {
        "input": 0.00002,
        "output": 0,  # embeddings no tienen output
    },
    "text-embedding-3-large": {
        "input": 0.00013,
        "output": 0,
    },
}


def calcular_costo(modelo: str, input_tokens: int, output_tokens: int = 0) -> dict:
    """
    Calcula el costo exacto de una solicitud al LLM.

    Args:
        modelo: Nombre del modelo (ej: 'gpt-4o-mini')
        input_tokens: Tokens de entrada (prompt + historial)
        output_tokens: Tokens de salida (respuesta generada)

    Returns:
        Dict con costo por componente y total
    """
    if modelo not in PRICING:
        raise ValueError(f"Modelo no reconocido: {modelo}. Opciones: {list(PRICING.keys())}")

    precio = PRICING[modelo]

    costo_entrada = (input_tokens / 1000) * precio["input"]
    costo_salida = (output_tokens / 1000) * precio["output"]
    costo_total = costo_entrada + costo_salida

    return {
        "modelo": modelo,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "costo_entrada": costo_entrada,
        "costo_salida": costo_salida,
        "costo_total": costo_total,
        "precio_entrada_por_1k": precio["input"],
        "precio_salida_por_1k": precio["output"],
    }


def mostrar_tabla_precios():
    """Muestra la tabla de precios de todos los modelos."""
    print("\n" + "=" * 80)
    print("TABLA DE PRECIOS DE OPENAI (USD por 1000 tokens)")
    print("=" * 80)
    print(f"{'Modelo':<30} {'Entrada (1K)':<15} {'Salida (1K)':<15}")
    print("-" * 80)

    for modelo, precios in PRICING.items():
        entrada = f"${precios['input']:.8f}"
        salida = f"${precios['output']:.8f}" if precios['output'] > 0 else "N/A"
        print(f"{modelo:<30} {entrada:<15} {salida:<15}")

    print("=" * 80)


def ejemplo_interactivo():
    """Permite calcular interactivamente el costo de una solicitud."""
    print("\n" + "=" * 80)
    print("CALCULADOR INTERACTIVO DE COSTO")
    print("=" * 80)

    print("\nModelos disponibles:")
    for i, modelo in enumerate(PRICING.keys(), 1):
        print(f"  {i}. {modelo}")

    # Seleccionar modelo
    while True:
        try:
            opcion = int(input("\nSelecciona un modelo (número): "))
            modelos_list = list(PRICING.keys())
            if 1 <= opcion <= len(modelos_list):
                modelo = modelos_list[opcion - 1]
                break
            else:
                print(f"Selecciona un número entre 1 y {len(modelos_list)}")
        except ValueError:
            print("Ingresa un número válido")

    # Ingresar tokens
    while True:
        try:
            input_tokens = int(input("\nTokens de entrada (prompt + historial): "))
            if input_tokens >= 0:
                break
            print("Ingresa un número positivo")
        except ValueError:
            print("Ingresa un número válido")

    # Ingresar output_tokens (optional para embeddings)
    output_tokens = 0
    if "embedding" not in modelo.lower():
        while True:
            try:
                output_tokens = int(input("Tokens de salida (respuesta generada, enter=0): ") or "0")
                if output_tokens >= 0:
                    break
                print("Ingresa un número positivo")
            except ValueError:
                print("Ingresa un número válido")

    # Calcular
    resultado = calcular_costo(modelo, input_tokens, output_tokens)

    # Mostrar resultado
    print("\n" + "-" * 80)
    print("RESULTADO:")
    print("-" * 80)
    print(f"Modelo:              {resultado['modelo']}")
    print(f"Tokens entrada:      {resultado['input_tokens']:,}")
    print(f"Tokens salida:       {resultado['output_tokens']:,}")
    print(f"Costo entrada:       ${resultado['costo_entrada']:.8f}")
    print(f"Costo salida:        ${resultado['costo_salida']:.8f}")
    print(f"COSTO TOTAL:         ${resultado['costo_total']:.8f}")
    print(f"\nEn centavos:         ¢{resultado['costo_total'] * 100:.4f}")
    print(f"En pesos (x 4000):   ${resultado['costo_total'] * 4000:.2f} COP")
    print("-" * 80)


def ejemplos_reales():
    """Muestra ejemplos de costos reales de solicitudes típicas."""
    print("\n" + "=" * 80)
    print("EJEMPLOS DE COSTOS REALES")
    print("=" * 80)

    ejemplos = [
        {
            "nombre": "Pregunta corta + respuesta corta",
            "modelo": "gpt-4o-mini",
            "input": 50,
            "output": 100,
        },
        {
            "nombre": "Pregunta con historial largo + respuesta media",
            "modelo": "gpt-4o-mini",
            "input": 2000,
            "output": 500,
        },
        {
            "nombre": "Análisis de documento grande (gpt-4o)",
            "modelo": "gpt-4o",
            "input": 5000,
            "output": 1000,
        },
        {
            "nombre": "Embedding de un párrafo",
            "modelo": "text-embedding-3-small",
            "input": 200,
            "output": 0,
        },
        {
            "nombre": "Batch de 100 embeddings pequeños",
            "modelo": "text-embedding-3-small",
            "input": 20000,  # 100 × 200 tokens
            "output": 0,
        },
    ]

    for ejemplo in ejemplos:
        resultado = calcular_costo(ejemplo["modelo"], ejemplo["input"], ejemplo["output"])
        print(f"\n{ejemplo['nombre']}")
        print(f"  Modelo: {resultado['modelo']}")
        print(f"  Tokens: {resultado['input_tokens']:,} entrada + {resultado['output_tokens']:,} salida")
        print(f"  💰 Costo: ${resultado['costo_total']:.8f} (¢{resultado['costo_total'] * 100:.4f})")


def main():
    """Menú principal."""
    while True:
        print("\n" + "=" * 80)
        print("CALCULADORA DE COSTO DE SOLICITUD AL LLM")
        print("=" * 80)
        print("\nOpciones:")
        print("  1. Ver tabla de precios")
        print("  2. Calcular costo de una solicitud (interactivo)")
        print("  3. Ver ejemplos de costos reales")
        print("  4. Salir")

        opcion = input("\nSelecciona una opción (1-4): ").strip()

        if opcion == "1":
            mostrar_tabla_precios()
        elif opcion == "2":
            try:
                ejemplo_interactivo()
                otra = input("\n¿Calcular otro? (s/n): ").strip().lower()
                if otra != 's':
                    break
            except Exception as e:
                print(f"Error: {e}")
        elif opcion == "3":
            ejemplos_reales()
        elif opcion == "4":
            print("\n¡Hasta luego!")
            break
        else:
            print("Opción no válida")


if __name__ == "__main__":
    main()
