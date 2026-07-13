def formatear_horario(valor: str) -> str:
    valor = valor.strip()
    if not valor:
        return ""
    if ":" in valor:
        valor = valor.replace(":", "")
    if not valor.isdigit():
        return valor

    if len(valor) > 4:
        raise ValueError(f"Formato de horario inválido: '{valor}' (demasiados dígitos)")

    if len(valor) <= 2:
        if int(valor) < 23:
            hora, minutos = int(valor), 0
        else:
            hora, minutos = int(valor[0]), int(valor[1])
    elif len(valor) == 3:
        hora, minutos = int(valor[0]), int(valor[1:])
    else:
        hora, minutos = int(valor[:2]), int(valor[2:])
        
    if minutos >= 60:
        hora += minutos // 60
        minutos %= 60

    hora, minutos = ajustar_hora_excedida(hora, minutos, valor)

    if not (0 <= minutos <= 59):
        raise ValueError(f"Minutos inválidos en '{valor}': {minutos} (debe ser 0-59)")

    return f"{hora:02d}:{minutos:02d}"

def ajustar_hora_excedida(hora: int, minutos: int, original: str) -> tuple[int, int]:
    """
    Corrige una hora >= 24 asumiendo que el usuario tipeó un 0 de más
    Saca el último dígito y reinterpreta como H + MM, con acarreo si
    los minutos resultantes superan 59.
    """
    if hora < 24 and minutos < 60:
        return hora, minutos
    

    if not original.endswith("0"):
        raise ValueError(f"Hora inválida en '{original}': {hora} (debe ser 0-23)")

    recortado = original[:-1]  # saca el último dígito
    if len(recortado) != 3 or not recortado.isdigit():
        raise ValueError(f"Hora inválida en '{original}': {hora} (debe ser 0-23)")

    nueva_hora = int(recortado[0])
    nuevos_min = int(recortado[1:])

    if nuevos_min >= 60:
        nueva_hora += nuevos_min // 60
        nuevos_min %= 60

    if not (0 <= nueva_hora <= 23):
        raise ValueError(f"Hora inválida en '{original}': no se pudo corregir")

    return nueva_hora, nuevos_min