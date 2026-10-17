import uvicorn

if __name__ == "__main__":
    # Permite abrir o painel móvel de outro dispositivo na mesma rede Wi-Fi.
    uvicorn.run("dashboard.app:app", host="0.0.0.0", port=8000, reload=False)
