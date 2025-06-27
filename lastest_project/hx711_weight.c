#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <gpiod.h>
#include <time.h>
#include <sched.h>
#include <string.h>

#define SCK_PIN  17  
#define DOUT_PIN 18  

// 全局变量
struct gpiod_chip *chip;  
struct gpiod_line *sck, *dout; 
const char *chipname = "gpiochip0"; 

int init_hx711() {
    chip = gpiod_chip_open_by_name(chipname);
    if (!chip) {
        perror("Error opening GPIO chip");
        return -1;
    }
    
    // 获取 SCK 和 DOUT 引脚
    sck = gpiod_chip_get_line(chip, SCK_PIN);
    dout = gpiod_chip_get_line(chip, DOUT_PIN);
    if (!sck || !dout) {
        perror("Error getting GPIO lines");
        return -1;
    }
    
    if (gpiod_line_request_output(sck, "hx711", 0) < 0) {
        perror("Error setting SCK as output");
        return -1;
    }
    if (gpiod_line_request_input(dout, "hx711") < 0) {
        perror("Error setting DOUT as input");
        return -1;
    }
    
    // 初始状态：SCK 低电平
    gpiod_line_set_value(sck, 0);
    return 0;
}

// 读取 HX711 数据（24位 ADC 值）
int32_t hx711_read() {
    int32_t count = 0;
    
    while (gpiod_line_get_value(dout) == 1) {
        usleep(10); // 防止忙等待
    }
    
    for (int i = 0; i < 24; i++) {
        gpiod_line_set_value(sck, 1); // 上升沿触发
        usleep(1);                    // 保持高电平
        count <<= 1;                  // 左移存储新位
        gpiod_line_set_value(sck, 0); // 下降沿完成位传输
        usleep(1);
        if (gpiod_line_get_value(dout) == 1) {
            count |= 1; // 设置当前位为 1
        }
    }
    
    gpiod_line_set_value(sck, 1);
    count ^= 0x800000; // 补码转原码
    usleep(1);
    gpiod_line_set_value(sck, 0);
    return count;
}

void cleanup() {
    if (sck) gpiod_line_release(sck);
    if (dout) gpiod_line_release(dout);
    if (chip) gpiod_chip_close(chip);
}

int set_cpu_affinity(int cpu_id) {
    cpu_set_t mask;
    CPU_ZERO(&mask);
    CPU_SET(cpu_id, &mask);
    
    if (sched_setaffinity(0, sizeof(mask), &mask) < 0) {
        perror("sched_setaffinity");
        return -1;
    }
    return 0;
}

int main() {
    if (set_cpu_affinity(2) < 0) {
        fprintf(stderr, "Failed to set CPU affinity\n");
        return 1;
    }
    
    // 初始化
    if (init_hx711() < 0) {
        fprintf(stderr, "HX711 initialization failed\n");
        return 1;
    }
    
    int32_t tare_value = hx711_read();
    printf("Tare value (zero offset): %d\n", tare_value);
    
    float weight_sum = 0;
    int samples = 10;
    
    for(int i = 0; i < samples; i++) {
        int32_t raw = hx711_read();
        float weight = (raw - tare_value) / 106.5f; 
        weight_sum += weight;
        usleep(100000); // 100ms
    }
    
    float average_weight = weight_sum / samples;
    printf("Average weight: %.2f grams\n", average_weight);
    
    FILE *fp = fopen("weight_data.txt", "w");
    if (fp) {
        fprintf(fp, "%.2f", average_weight);
        fclose(fp);
        printf("Weight data saved to weight_data.txt\n");
    } else {
        perror("Failed to save weight data");
    }
    
    cleanup();
    return 0;
}

