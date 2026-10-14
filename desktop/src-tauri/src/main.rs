// Evita una consola extra en Windows en las versiones publicadas.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    radar_bolsa_lib::run()
}
