"""Geração de relatório textual das rotas."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from utils.helpers import format_duration


def build_text_report(
    summary: dict[str, Any],
    stats: dict[str, float | int],
    map_path: str | Path | None,
) -> str:
    """Monta o relatório textual de uma rota.

    Args:
        summary: Dicionário retornado por ``analyze_route``.
        stats: Dicionário retornado por ``calculate_route_stats``.
        map_path: Caminho do mapa HTML, quando gerado.

    Returns:
        Relatório pronto para impressão no console.
    """
    route_date = summary["data_rota"].strftime("%d/%m/%Y")
    start = summary["inicio"].strftime("%H:%M")
    end = summary["fim"].strftime("%H:%M")
    moving = format_duration(float(summary["tempo_movimento_segundos"]))
    stopped = format_duration(float(summary["tempo_parado_segundos"]))
    map_line = str(map_path) if map_path else "não gerado"

    return (
        "\n===== RELATÓRIO DE ROTA =====\n"
        f"Veículo   : {summary['Veículo']} — {summary['Placa']}\n"
        f"Data      : {route_date}\n"
        f"Início    : {start}   Fim: {end}\n"
        f"Distância : {summary['distancia_km']:.1f} km\n"
        f"Em movimento: {moving}  Parado: {stopped}\n"
        f"Vel. Média: {float(stats['velocidade_media']):.1f} km/h   "
        f"Vel. Máx: {float(stats['velocidade_maxima']):.1f} km/h\n"
        f"Alertas de velocidade: {int(stats['alertas_velocidade'])}\n"
        f"Paradas   : {int(stats['quantidade_paradas'])} "
        f"(duração média: {float(stats['duracao_media_parada_minutos']):.1f} min)\n"
        f"Ignição   : ligada {float(stats['percentual_ignicao_ligada']):.1f}%   "
        f"desligada {float(stats['percentual_ignicao_desligada']):.1f}%\n"
        f"Mapa salvo em: {map_line}\n"
    )


def print_report(
    summary: dict[str, Any],
    stats: dict[str, float | int],
    map_path: str | Path | None,
) -> None:
    """Imprime o relatório textual no console.

    Args:
        summary: Dicionário da rota.
        stats: Estatísticas da rota.
        map_path: Caminho do mapa HTML, quando gerado.
    """
    print(build_text_report(summary, stats, map_path))
