def load_env_fallback():
    """
    Ręcznie wczytuje plik .env do os.environ z pełną diagnostyką w konsoli.
    """
    if os.getenv("GEMINI_API_KEY"):
        return

    possible_paths = [
        Path(".env"),                                      # Bieżący folder roboczy
        Path("backend/.env"),                              # Folder backend
        Path(__file__).resolve().parent.parent.parent / ".env"  # Ścieżka relatywna do serwisu
    ]

    print(f"\n🔍 [DIAGNOSTYKA .ENV] Bieżący katalog roboczy (CWD): {os.getcwd()}")
    
    found_any = False
    for path_obj in possible_paths:
        resolved_path = path_obj.resolve()
        exists = resolved_path.exists()
        print(f"👉 Sprawdzam ścieżkę: {resolved_path} -> [Znaleziono: {'TAK' if exists else 'NIE'}]")
        
        if exists:
            found_any = True
            print(f"📖 Próba wczytania pliku: {resolved_path}")
            try:
                loaded_keys = []
                with open(resolved_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, val = line.split("=", 1)
                            k_clean = key.strip()
                            v_clean = val.strip().strip("'\"")
                            os.environ[k_clean] = v_clean
                            loaded_keys.append(k_clean)
                print(f"✅ Pomyślnie wczytano klucze z pliku: {loaded_keys}")
                break
            except Exception as e:
                print(f"❌ Błąd odczytu pliku .env: {e}")
                
    if not found_any:
        print("❌ Nie znaleziono pliku .env w żadnej z badanych lokalizacji!")
        
    final_key = os.getenv("GEMINI_API_KEY")
    print(f"🔑 Status GEMINI_API_KEY: {'ZNAJDZIONO (zaczyna się od: ' + final_key[:6] + '...)' if final_key else 'NIE ZNAJDZIONO!'}\n")