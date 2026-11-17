"""
title: Herramientas del modo
description: Activa en cada mensaje las herramientas asignadas al modo (Open WebUI solo las manda en el primero del chat).
version: 1.0
"""


class Filter:
    def inlet(self, body: dict, __metadata__: dict = None, __model__: dict = None) -> dict:
        ids = (((__model__ or {}).get("info") or {}).get("meta") or {}).get("toolIds") or []
        # en body y no en metadata: el middleware relee tool_ids del body tras los filtros y pisa metadata
        if ids and not (__metadata__ or {}).get("task") and not body.get("tool_ids"):  # task = título/etiquetas
            body["tool_ids"] = list(ids)
        return body
