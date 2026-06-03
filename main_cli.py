"""Ponto de entrada da análise de rastreamento GPS de frota."""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

from core.routes import analyze_route, filter_stops_for_route, iter_vehicle_day_routes
from core.stats import calculate_route_stats
from config import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SPEED_LIMIT_KMH,
    DEFAULT_STOP_MINUTES,
)
from core.loader import load_csv_file, load_csv_folder
from core.processor import classify_stops, filter_by_date, filter_by_vehicle, sort_records
from utils.helpers import ensure_directory, parse_brazilian_date, sanitize_filename
from core.map_builder import build_route_map
from core.report import print_report


def build_parser() -> argparse.ArgumentParser:
    """Cria o parser de argumentos da linha de comando.

    Returns:
        Parser configurado.
    """
    parser = argparse.ArgumentParser(
        description="Analisa CSVs de rastreamento GPS e gera relatórios de frota."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--arquivo", type=Path, help="Arquivo CSV de entrada.")
    source.add_argument("--pasta", type=Path, help="Pasta com arquivos CSV de entrada.")

    parser.add_argument("--veiculo", help="Nome do veículo ou placa para filtrar.")
    parser.add_argument(
        "--data",
        help="Data da análise no formato dd/mm/aaaa. Padrão: dia anterior.",
    )
    parser.add_argument(
        "--limite-velocidade",
        type=float,
        default=DEFAULT_SPEED_LIMIT_KMH,
        help=f"Limite de velocidade em km/h. Padrão: {DEFAULT_SPEED_LIMIT_KMH:.0f}.",
    )
    parser.add_argument(
        "--saida",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Pasta de saída dos mapas HTML. Padrão: {DEFAULT_OUTPUT_DIR}.",
    )
    parser.add_argument(
        "--sem-mapa",
        action="store_true",
        help="Gera apenas o relatório textual, sem mapa HTML.",
    )
    parser.add_argument(
        "--min-parada",
        type=int,
        default=DEFAULT_STOP_MINUTES,
        help=f"Duração mínima de parada, em minutos. Padrão: {DEFAULT_STOP_MINUTES}.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Executa a aplicação pela linha de comando.

    Args:
        argv: Argumentos opcionais, úteis para testes.

    Returns:
        Código de saída do processo.
    """
    _configure_output_encoding()
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        target_date = _resolve_target_date(args.data)
        print(f"🔎 Data analisada: {target_date:%d/%m/%Y}")

        if args.arquivo:
            df = load_csv_file(args.arquivo)
        else:
            df = load_csv_folder(args.pasta)

        filtered = filter_by_vehicle(df, args.veiculo)
        filtered = filter_by_date(filtered, target_date)
        filtered = sort_records(filtered)

        if filtered.empty:
            vehicle_message = f" e veículo/placa {args.veiculo!r}" if args.veiculo else ""
            print(
                "⚠️ Nenhum dado encontrado para "
                f"{target_date:%d/%m/%Y}{vehicle_message}."
            )
            return 0

        filtered, stops = classify_stops(filtered, min_stop_minutes=args.min_parada)
        output_dir = ensure_directory(args.saida) if not args.sem_mapa else args.saida

        route_count = 0
        for (vehicle, plate, route_date), route_df in iter_vehicle_day_routes(filtered):
            route_stops = filter_stops_for_route(stops, vehicle, plate, route_date)
            summary = analyze_route(route_df, route_stops)
            stats = calculate_route_stats(route_df, route_stops, args.limite_velocidade)

            map_path = None
            if not args.sem_mapa:
                map_path = _build_map_path(output_dir, vehicle, plate, route_date)
                map_path = build_route_map(
                    route_df,
                    route_stops,
                    map_path,
                    args.limite_velocidade,
                )

            print_report(summary, stats, map_path)
            route_count += 1

        print(f"✅ {route_count} rota(s) processada(s).")
        return 0
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"❌ {exc}")
        return 1
    except KeyboardInterrupt:
        print("\n⚠️ Execução interrompida pelo usuário.")
        return 130


def _resolve_target_date(value: str | None) -> date:
    if value:
        return parse_brazilian_date(value)
    return date.today() - timedelta(days=1)


def _configure_output_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except OSError:
                pass


def _build_map_path(output_dir: Path, vehicle: str, plate: str, route_date: object) -> Path:
    date_text = route_date.strftime("%Y-%m-%d") if hasattr(route_date, "strftime") else str(route_date)
    filename = sanitize_filename(f"{date_text}_{vehicle}_{plate}") + ".html"
    return output_dir / filename


if __name__ == "__main__":
    sys.exit(main())
