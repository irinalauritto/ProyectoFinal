/*
  emg_esp32.c

  Adquisición de la señal EMG (salida SIG, ya rectificada y filtrada -
  envolvente) del sensor MyoWare 2.0 mediante el ADC de la ESP32, y envío
  continuo por puerto serie para su procesamiento y visualización en la
  interfaz Python.

  Placa: ESP32-C6.

  Conexionado en el header de 3 pines +/-/SIG del MyoWare
    MyoWare +   -> ESP32-C6 3.3V  
    MyoWare -   -> ESP32-C6 GND
    MyoWare SIG -> ESP32-C6 GPIO1  (ADC1_CHANNEL_1)

*/

#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_adc/adc_oneshot.h"

#define EMG_ADC_CHANNEL   ADC_CHANNEL_1   // GPIO1 en ADC1
#define SAMPLE_DELAY_MS   2                // ~500 Hz de muestreo aproximado

void app_main(void)
{
    adc_oneshot_unit_handle_t adc1_handle;
    adc_oneshot_unit_init_cfg_t init_cfg = {
        .unit_id = ADC_UNIT_1,
    };
    ESP_ERROR_CHECK(adc_oneshot_new_unit(&init_cfg, &adc1_handle));

    adc_oneshot_chan_cfg_t chan_cfg = {
        .bitwidth = ADC_BITWIDTH_12,   // Resolución 0-4095
        .atten = ADC_ATTEN_DB_12,      // Rango completo 0-3.3V
    };
    ESP_ERROR_CHECK(adc_oneshot_config_channel(adc1_handle, EMG_ADC_CHANNEL, &chan_cfg));

    int value;
    while (1) {
        ESP_ERROR_CHECK(adc_oneshot_read(adc1_handle, EMG_ADC_CHANNEL, &value));
        printf("%d\n", value);
        vTaskDelay(pdMS_TO_TICKS(SAMPLE_DELAY_MS));
    }
}
C:\Python314\python.exe "C:\Tesis\interfaz_emg\src\emg_plot.py"C:\Python314\python.exe "C:\Tesis\interfaz_emg\src\emg_plot.py"