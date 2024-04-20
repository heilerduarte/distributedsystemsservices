import socket
import threading
import time
import base64
import urllib.parse
from cryptography.fernet import Fernet
import os
import tkinter as tk
from tkinter import Listbox, Label, Frame, Button, Toplevel
import requests

# Clave de encriptación
clave_encriptacion = b'DG-cgQo2hRFJCCq4sZlyQWZtPUzTczxoSeG0RmQvaQA='
cipher_suite = Fernet(clave_encriptacion)

# Carpeta compartida para archivos
CARPETA_COMPARTIDA = 'archivos_compartidos'

# Conjunto de pares conectados
PEERS = set()

# Puerto para broadcast
BROADCAST_PORT = 9876

# Puerto del servidor
SERVER_PORT = 5000

# IP local
LOCAL_IP = socket.gethostbyname(socket.gethostname())

# Función para cifrar las credenciales
def cifrar_credenciales(usuario, clave):
    usuario_cifrado = cipher_suite.encrypt(usuario.encode())
    clave_cifrado = cipher_suite.encrypt(clave.encode())
    return usuario_cifrado, clave_cifrado

# Función para descifrar las credenciales
def descifrar_credenciales(usuario_cifrado, clave_cifrado):
    usuario = cipher_suite.decrypt(usuario_cifrado).decode()
    clave = cipher_suite.decrypt(clave_cifrado).decode()
    return usuario, clave

# Función para validar credenciales (implementa tu lógica de validación aquí)
def validar_credenciales(usuario, clave):
    # Por ejemplo, simplemente verificar si las credenciales son "usuario" y "contraseña"
    return usuario == "usuario" and clave == "contraseña"

# Función para listar archivos locales
def listar_archivos_locales():
    archivos = os.listdir(CARPETA_COMPARTIDA)
    return archivos

# Función para listar archivos remotos
def listar_archivos_remotos():
    archivos_remotos = set()
    for peer in PEERS:
        try:
            response = requests.get(f'http://{peer}:{SERVER_PORT}/archivos')
            if response.status_code == 200:
                for archivo in response.json():
                    archivos_remotos.add(f"{peer} {archivo}")  # Agregar la dirección IP del peer al nombre del archivo
        except Exception as e:
            print(e)
    return archivos_remotos

# Función para descargar archivo seleccionado
def descargar_seleccionado():
    archivo_completo = lista_archivos_remotos.get(tk.ACTIVE)
    if archivo_completo:
        partes = archivo_completo.split(None, 1)
        if len(partes) >= 2:
            archivo_seleccionado = partes[1]
            peer_ip = partes[0]
            url = f'http://{peer_ip}:{SERVER_PORT}/archivos/{urllib.parse.quote(archivo_seleccionado)}'
            try:
                response = requests.get(url)
                response.raise_for_status()  
                file_content = base64.b64decode(response.content)
                with open(os.path.join(CARPETA_COMPARTIDA, archivo_seleccionado), 'wb') as f:
                    f.write(file_content)
                actualizar_lista_archivos_locales()
            except Exception as e:
                print("Error al descargar el archivo:", e)
        else:
            print("La lista de archivos remotos no tiene suficientes partes.")
    else:
        print("Ningún archivo seleccionado. Por favor, seleccione un archivo para descargar.")

# Función para actualizar lista de archivos locales
def actualizar_lista_archivos_locales():
    lista_archivos_locales.delete(0, tk.END)
    for archivo in listar_archivos_locales():
        lista_archivos_locales.insert(tk.END, archivo)

# Función para actualizar lista de archivos remotos
def actualizar_lista_archivos_remotos():
    lista_archivos_remotos.delete(0, tk.END)
    for archivo in listar_archivos_remotos():
        lista_archivos_remotos.insert(tk.END, archivo)

# Función para enviar broadcast con usuario y clave
def enviar_broadcast():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while True:
            usuario = "usuario"
            clave = "contraseña"
            usuario_cifrado, clave_cifrado = cifrar_credenciales(usuario, clave)
            mensaje = f'{usuario_cifrado.decode()}:{clave_cifrado.decode()}'
            s.sendto(mensaje.encode(), ('<broadcast>', BROADCAST_PORT))
            time.sleep(10)

# Función para escuchar broadcast y validar credenciales
def escuchar_broadcast():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('', BROADCAST_PORT))
        while True:
            data, addr = s.recvfrom(1024)
            usuario_cifrado, clave_cifrado = data.decode().split(':')
            usuario, clave = descifrar_credenciales(usuario_cifrado.encode(), clave_cifrado.encode())
            # Validar las credenciales aquí
            if validar_credenciales(usuario, clave):
                PEERS.add(addr[0])  # Agregar el par solo si las credenciales son válidas
                actualizar_lista_archivos_remotos()
            else:
                print(f'Credenciales inválidas recibidas de {addr[0]}')

# Función principal de la interfaz gráfica
def gui():
    global lista_archivos_locales, lista_archivos_remotos
    ventana = tk.Tk()
    ventana.title("Red P2P con GUI")

    frame_locales = Frame(ventana)
    frame_locales.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    Label(frame_locales, text="Archivos Locales").pack()
    lista_archivos_locales = Listbox(frame_locales)
    lista_archivos_locales.pack(fill=tk.BOTH, expand=True)
    
    frame_remotos = Frame(ventana)
    frame_remotos.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
    Label(frame_remotos, text="Archivos en Peers").pack()
    lista_archivos_remotos = Listbox(frame_remotos)
    lista_archivos_remotos.pack(fill=tk.BOTH, expand=True)

    button_descargar = Button(frame_remotos, text="Descargar seleccionado", command=descargar_seleccionado)
    button_descargar.pack()
    
    threading.Thread(target=iniciar_servidor, daemon=True).start()
    threading.Thread(target=enviar_broadcast, daemon=True).start()
    threading.Thread(target=escuchar_broadcast, daemon=True).start()
    threading.Thread(target=actualizar_lista_archivos_locales, daemon=True).start()
    threading.Thread(target=actualizar_lista_archivos_remotos, daemon=True).start()
    
    ventana.mainloop()

if __name__ == "__main__":
    # Crear carpeta compartida si no existe
    if not os.path.exists(CARPETA_COMPARTIDA):
        os.makedirs(CARPETA_COMPARTIDA)
    # Iniciar GUI
    gui()
