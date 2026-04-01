"""Narzędzia kontroli współbieżności (wersja zoptymalizowana)

Ulepszenia wydajności:
1. Dynamiczne ograniczenie współbieżności (na podstawie obciążenia systemu)
2. Oddzielna kontrola współbieżności dla różnych typów weryfikacji
3. Obsługa większej liczby równoległych zadań
4. Monitorowanie obciążenia i automatyczna regulacja
"""
import asyncio
import logging
from typing import Dict
import psutil

logger = logging.getLogger(__name__)

# Dynamiczne obliczanie maksymalnej liczby współbieżnych zadań
def _calculate_max_concurrency() -> int:
    """Oblicza maksymalną współbieżność na podstawie zasobów systemowych"""
    try:
        cpu_count = psutil.cpu_count() or 4
        memory_gb = psutil.virtual_memory().total / (1024 ** 3)
        
        # Obliczenia na podstawie CPU i pamięci
        # Każdy rdzeń CPU obsługuje 3–5 zadań równoległych
        # Każdy GB RAM obsługuje 2 zadania równoległe
        cpu_based = cpu_count * 4
        memory_based = int(memory_gb * 2)
        
        # Bierzemy minimum i ustawiamy zakres
        max_concurrent = min(cpu_based, memory_based)
        max_concurrent = max(10, min(max_concurrent, 100))  # zakres 10–100
        
        logger.info(
            f"Zasoby systemu: CPU={cpu_count}, Memory={memory_gb:.1f}GB, "
            f"obliczona współbieżność={max_concurrent}"
        )
        
        return max_concurrent
        
    except Exception as e:
        logger.warning(f"Nie można pobrać informacji o systemie: {e}, używam wartości domyślnej")
        return 20  # wartość domyślna

# Obliczenie bazowego limitu współbieżności
_base_concurrency = _calculate_max_concurrency()

# Tworzymy osobne semafory dla różnych typów weryfikacji
# Dzięki temu jeden typ nie blokuje innych
_verification_semaphores: Dict[str, asyncio.Semaphore] = {
    "gemini_one_pro": asyncio.Semaphore(_base_concurrency // 5),
    "chatgpt_teacher_k12": asyncio.Semaphore(_base_concurrency // 5),
    "spotify_student": asyncio.Semaphore(_base_concurrency // 5),
    "youtube_student": asyncio.Semaphore(_base_concurrency // 5),
    "bolt_teacher": asyncio.Semaphore(_base_concurrency // 5),
}


def get_verification_semaphore(verification_type: str) -> asyncio.Semaphore:
    """Pobiera semafor dla danego typu weryfikacji
    
    Args:
        verification_type: typ weryfikacji
        
    Returns:
        asyncio.Semaphore: odpowiedni semafor
    """
    semaphore = _verification_semaphores.get(verification_type)
    
    if semaphore is None:
        # Nieznany typ — tworzymy domyślny semafor
        semaphore = asyncio.Semaphore(_base_concurrency // 3)
        _verification_semaphores[verification_type] = semaphore
        logger.info(
            f"Utworzono semafor dla nowego typu {verification_type}: "
            f"limit={_base_concurrency // 3}"
        )
    
    return semaphore


def get_concurrency_stats() -> Dict[str, Dict[str, int]]:
    """Pobiera statystyki współbieżności
    
    Returns:
        dict: informacje o współbieżności dla każdego typu
    """
    stats = {}
    for vtype, semaphore in _verification_semaphores.items():
        # Uwaga: _value to wewnętrzne pole (może się różnić między wersjami Pythona)
        try:
            available = semaphore._value if hasattr(semaphore, '_value') else 0
            limit = _base_concurrency // 3
            in_use = limit - available
        except Exception:
            available = 0
            limit = _base_concurrency // 3
            in_use = 0
        
        stats[vtype] = {
            'limit': limit,
            'in_use': in_use,
            'available': available,
        }
    
    return stats


async def monitor_system_load() -> Dict[str, float]:
    """Monitoruje obciążenie systemu
    
    Returns:
        dict: informacje o obciążeniu systemu
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_percent = psutil.virtual_memory().percent
        
        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory_percent,
            'concurrency_limit': _base_concurrency,
        }
    except Exception as e:
        logger.error(f"Błąd monitorowania systemu: {e}")
        return {
            'cpu_percent': 0.0,
            'memory_percent': 0.0,
            'concurrency_limit': _base_concurrency,
        }


def adjust_concurrency_limits(multiplier: float = 1.0):
    """Dynamicznie dostosowuje limit współbieżności
    
    Args:
        multiplier: mnożnik (0.5–2.0)
    """
    global _verification_semaphores, _base_concurrency
    
    # Ograniczenie zakresu
    multiplier = max(0.5, min(multiplier, 2.0))
    
    new_base = int(_base_concurrency * multiplier)
    new_limit = max(5, min(new_base // 3, 50))  # na typ: 5–50
    
    logger.info(
        f"Dostosowanie współbieżności: multiplier={multiplier}, "
        f"new_base={new_base}, per_type={new_limit}"
    )
    
    # Tworzymy nowe semafory
    for vtype in _verification_semaphores.keys():
        _verification_semaphores[vtype] = asyncio.Semaphore(new_limit)


# Zadanie monitorujące obciążenie
_monitor_task = None

async def start_load_monitoring(interval: float = 60.0):
    """Uruchamia monitorowanie obciążenia
    
    Args:
        interval: czas między pomiarami (sekundy)
    """
    global _monitor_task
    
    if _monitor_task is not None:
        return
    
    async def monitor_loop():
        while True:
            try:
                await asyncio.sleep(interval)
                
                load_info = await monitor_system_load()
                cpu = load_info['cpu_percent']
                memory = load_info['memory_percent']
                
                logger.info(
                    f"Obciążenie systemu: CPU={cpu:.1f}%, Memory={memory:.1f}%"
                )
                
                # Automatyczna regulacja
                if cpu > 80 or memory > 85:
                    # Za duże obciążenie — zmniejszamy
                    adjust_concurrency_limits(0.7)
                    logger.warning("Zbyt duże obciążenie — zmniejszono współbieżność")
                elif cpu < 40 and memory < 60:
                    # Małe obciążenie — zwiększamy
                    adjust_concurrency_limits(1.2)
                    logger.info("Niskie obciążenie — zwiększono współbieżność")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Błąd monitorowania: {e}")
    
    _monitor_task = asyncio.create_task(monitor_loop())
    logger.info(f"Monitorowanie uruchomione: interval={interval}s")


async def stop_load_monitoring():
    """Zatrzymuje monitorowanie obciążenia"""
    global _monitor_task
    
    if _monitor_task is not None:
        _monitor_task.cancel()
        try:
            await _monitor_task
        except asyncio.CancelledError:
            pass
        _monitor_task = None
        logger.info("Monitorowanie zatrzymane")
        
