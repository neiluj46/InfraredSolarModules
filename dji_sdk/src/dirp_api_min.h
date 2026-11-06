/*
 * Sous-ensemble de l'API du DJI Thermal SDK (libdirp), v1.x.
 *
 * Le fichier d'en-tête officiel (dirp_api.h) n'est livré qu'avec l'archive DJI.
 * Ces déclarations sont reconstituées à partir des symboles exportés par
 * libdirp.so v1.7 et des structures documentées par DJI (reprises par le
 * projet thermal_parser, MIT), puis vérifiées le 06/11/2026 contre le
 * dirp_api.h officiel du SDK v1.9 (dji_sdk/lib/, non versionné) : même
 * disposition mémoire pour tout ce qui est déclaré ici. Seules les fonctions
 * utilisées par dji_irp.c sont déclarées.
 */
#ifndef DIRP_API_MIN_H
#define DIRP_API_MIN_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef void *DIRP_HANDLE;

/* Codes de retour (dirp_ret_code_e) */
#define DIRP_SUCCESS                  0
#define DIRP_ERROR_MALLOC            -1
#define DIRP_ERROR_POINTER_NULL      -2
#define DIRP_ERROR_INVALID_PARAMS    -3
#define DIRP_ERROR_INVALID_RAW       -4
#define DIRP_ERROR_INVALID_HEADER    -5
#define DIRP_ERROR_INVALID_CURVE     -6
#define DIRP_ERROR_RJPEG_PARSE       -7
#define DIRP_ERROR_SIZE              -8
#define DIRP_ERROR_INVALID_HANDLE    -9
#define DIRP_ERROR_FORMAT_INPUT     -10
#define DIRP_ERROR_FORMAT_OUTPUT    -11
#define DIRP_ERROR_UNSUPPORTED_FUNC -12
#define DIRP_ERROR_NOT_READY        -13
#define DIRP_ERROR_ACTIVATION       -14
#define DIRP_ERROR_INVALID_INI      -15
#define DIRP_ERROR_INVALID_SUB_DLL  -16
#define DIRP_ERROR_ADVANCED         -32
#define DIRP_ERROR_SUPER_MODE       -64

/* Niveaux de verbosité (dirp_verbose_level_e) */
#define DIRP_VERBOSE_LEVEL_NONE   0
#define DIRP_VERBOSE_LEVEL_DEBUG  1
#define DIRP_VERBOSE_LEVEL_DETAIL 2

typedef struct {
    uint32_t rjpeg;   /* version du R-JPEG */
    uint32_t header;  /* version de l'en-tête */
    uint32_t curve;   /* version de la table de conversion (LUT) */
} dirp_rjpeg_version_t;

typedef struct {
    int32_t width;
    int32_t height;
} dirp_resolution_t;

typedef struct {
    float distance;    /* distance à la cible, m [1 ; 25] */
    float humidity;    /* humidité relative, % [20 ; 100] */
    float emissivity;  /* émissivité [0,10 ; 1,00] */
    float reflection;  /* température réfléchie, °C [-40 ; 500] */
    /* Ajouté dans le SDK v1.9 (absent de la v1.7) : sans lui, dirp_get_measurement_params
     * de la v1.9 écrit 4 octets au-delà de la structure. Une v1.7 ne le remplit pas. */
    float ambient_temp; /* température ambiante, °C */
} dirp_measurement_params_t;

typedef struct { float min; float max; } dirp_plage_t;
typedef struct {
    dirp_plage_t distance, humidity, emissivity, reflection, ambient_temp;
} dirp_measurement_params_range_t;

void    dirp_set_verbose_level(int32_t level);
int32_t dirp_create_from_rjpeg(const uint8_t *data, int32_t size, DIRP_HANDLE *ph);
int32_t dirp_destroy(DIRP_HANDLE h);
int32_t dirp_get_rjpeg_version(DIRP_HANDLE h, dirp_rjpeg_version_t *version);
int32_t dirp_get_rjpeg_resolution(DIRP_HANDLE h, dirp_resolution_t *resolution);
int32_t dirp_get_measurement_params(DIRP_HANDLE h, dirp_measurement_params_t *params);
int32_t dirp_set_measurement_params(DIRP_HANDLE h, const dirp_measurement_params_t *params);
/* SDK v1.9 (déclaration faible : absente d'une bibliothèque plus ancienne, le pointeur vaut alors NULL) */
int32_t dirp_get_measurement_params_range(DIRP_HANDLE h, dirp_measurement_params_range_t *range)
    __attribute__((weak));
/* size = taille du tampon en octets */
int32_t dirp_get_original_raw(DIRP_HANDLE h, uint16_t *raw_image, int32_t size);
int32_t dirp_measure(DIRP_HANDLE h, int16_t *temp_image, int32_t size);   /* 0,1 °C */
int32_t dirp_measure_ex(DIRP_HANDLE h, float *temp_image, int32_t size);  /* °C */

#ifdef __cplusplus
}
#endif

#endif
