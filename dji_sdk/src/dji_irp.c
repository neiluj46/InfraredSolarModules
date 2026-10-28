/*
 * dji_irp : outil en ligne de commande minimal au-dessus de libdirp (DJI Thermal SDK).
 *
 * Reprend les options principales de l'exemple officiel « dji_irp » du SDK :
 *
 *   dji_irp -s <entree.jpg> -a measure -o <sortie.raw> [--measurefmt float32|int16]
 *           [--distance m] [--humidity %] [--emissivity e] [--reflection °C]
 *   dji_irp -s <entree.jpg> -a extract -o <sortie.raw>      (RAW 16 bits du capteur)
 *   dji_irp -s <entree.jpg> -a info                         (JSON sur la sortie standard)
 *
 * Sortie « measure » : tableau brut, ligne par ligne, petit-boutiste,
 * float32 en °C (défaut) ou int16 en dixièmes de °C.
 */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "dirp_api_min.h"

static void usage(const char *prog)
{
    fprintf(stderr,
            "Utilisation : %s -s <entree.jpg> -a measure|extract|info [-o <sortie>]\n"
            "              [--measurefmt float32|int16] [--distance m] [--humidity %%]\n"
            "              [--emissivity e] [--reflection degC] [-v]\n",
            prog);
}

static const char *message(int32_t code)
{
    switch (code) {
    case DIRP_ERROR_MALLOC: return "échec d'allocation";
    case DIRP_ERROR_POINTER_NULL: return "pointeur nul";
    case DIRP_ERROR_INVALID_PARAMS: return "paramètres invalides";
    case DIRP_ERROR_INVALID_RAW: return "RAW invalide dans le R-JPEG";
    case DIRP_ERROR_INVALID_HEADER: return "en-tête R-JPEG invalide";
    case DIRP_ERROR_INVALID_CURVE: return "table de conversion invalide";
    case DIRP_ERROR_RJPEG_PARSE: return "fichier non reconnu comme R-JPEG DJI";
    case DIRP_ERROR_SIZE: return "taille incorrecte";
    case DIRP_ERROR_INVALID_HANDLE: return "poignée invalide";
    case DIRP_ERROR_UNSUPPORTED_FUNC: return "fonction non prise en charge pour ce modèle";
    case DIRP_ERROR_NOT_READY: return "conditions préalables non remplies";
    case DIRP_ERROR_ACTIVATION: return "activation du SDK refusée";
    default: return "erreur inconnue";
    }
}

static int lire_fichier(const char *chemin, uint8_t **donnees, long *taille)
{
    FILE *f = fopen(chemin, "rb");
    if (!f) {
        fprintf(stderr, "Impossible d'ouvrir %s : %s\n", chemin, strerror(errno));
        return -1;
    }
    fseek(f, 0, SEEK_END);
    *taille = ftell(f);
    fseek(f, 0, SEEK_SET);
    *donnees = malloc((size_t)*taille);
    if (!*donnees || fread(*donnees, 1, (size_t)*taille, f) != (size_t)*taille) {
        fprintf(stderr, "Lecture de %s impossible\n", chemin);
        fclose(f);
        free(*donnees);
        return -1;
    }
    fclose(f);
    return 0;
}

static int ecrire_fichier(const char *chemin, const void *donnees, size_t taille)
{
    FILE *f = fopen(chemin, "wb");
    if (!f) {
        fprintf(stderr, "Impossible d'écrire %s : %s\n", chemin, strerror(errno));
        return -1;
    }
    size_t n = fwrite(donnees, 1, taille, f);
    fclose(f);
    return n == taille ? 0 : -1;
}

int main(int argc, char **argv)
{
    const char *source = NULL, *action = NULL, *sortie = NULL, *format = "float32";
    float distance = -1, humidite = -1, emissivite = -1, reflexion = -1000;
    int verbeux = 0;

    for (int i = 1; i < argc; i++) {
        const char *a = argv[i];
        const char *v = i + 1 < argc ? argv[i + 1] : NULL;
        if (!strcmp(a, "-v")) { verbeux = 1; continue; }
        if (!strcmp(a, "-h") || !strcmp(a, "--help")) { usage(argv[0]); return 0; }
        if (!v) { usage(argv[0]); return 2; }
        if (!strcmp(a, "-s")) source = v;
        else if (!strcmp(a, "-a")) action = v;
        else if (!strcmp(a, "-o")) sortie = v;
        else if (!strcmp(a, "--measurefmt")) format = v;
        else if (!strcmp(a, "--distance")) distance = strtof(v, NULL);
        else if (!strcmp(a, "--humidity")) humidite = strtof(v, NULL);
        else if (!strcmp(a, "--emissivity")) emissivite = strtof(v, NULL);
        else if (!strcmp(a, "--reflection")) reflexion = strtof(v, NULL);
        else { fprintf(stderr, "Option inconnue : %s\n", a); usage(argv[0]); return 2; }
        i++;
    }
    if (!source || !action || (strcmp(action, "info") && !sortie)) {
        usage(argv[0]);
        return 2;
    }

    dirp_set_verbose_level(verbeux ? DIRP_VERBOSE_LEVEL_DEBUG : DIRP_VERBOSE_LEVEL_NONE);

    uint8_t *donnees = NULL;
    long taille = 0;
    if (lire_fichier(source, &donnees, &taille))
        return 1;

    DIRP_HANDLE h = NULL;
    int32_t ret = dirp_create_from_rjpeg(donnees, (int32_t)taille, &h);
    if (ret != DIRP_SUCCESS) {
        fprintf(stderr, "dirp_create_from_rjpeg(%s) : %d (%s)\n", source, ret, message(ret));
        free(donnees);
        return 3;
    }

    int code = 0;
    dirp_resolution_t res = {0};
    dirp_get_rjpeg_resolution(h, &res);
    size_t n = (size_t)res.width * res.height;

    /* Paramètres de mesure : non pris en charge par tous les modèles (M2EA : -12). */
    dirp_measurement_params_t params;
    int32_t ret_params = dirp_get_measurement_params(h, &params);
    int modifie = distance >= 0 || humidite >= 0 || emissivite >= 0 || reflexion > -1000;
    if (modifie) {
        if (ret_params != DIRP_SUCCESS) {
            fprintf(stderr, "Paramètres de mesure non réglables pour ce fichier : %d (%s)\n",
                    ret_params, message(ret_params));
            code = 4;
            goto fin;
        }
        if (distance >= 0) params.distance = distance;
        if (humidite >= 0) params.humidity = humidite;
        if (emissivite >= 0) params.emissivity = emissivite;
        if (reflexion > -1000) params.reflection = reflexion;
        ret = dirp_set_measurement_params(h, &params);
        if (ret != DIRP_SUCCESS) {
            fprintf(stderr, "dirp_set_measurement_params : %d (%s)\n", ret, message(ret));
            code = 4;
            goto fin;
        }
    }

    if (!strcmp(action, "info")) {
        dirp_rjpeg_version_t ver = {0};
        dirp_get_rjpeg_version(h, &ver);
        printf("{\"width\": %u, \"height\": %u, \"rjpeg_version\": %u, \"header_version\": %u, "
               "\"curve_version\": %u",
               res.width, res.height, ver.rjpeg, ver.header, ver.curve);
        if (ret_params == DIRP_SUCCESS)
            printf(", \"measurement_params\": {\"distance\": %g, \"humidity\": %g, "
                   "\"emissivity\": %g, \"reflection\": %g}}\n",
                   params.distance, params.humidity, params.emissivity, params.reflection);
        else
            printf(", \"measurement_params\": null}\n");
    } else if (!strcmp(action, "measure")) {
        if (!strcmp(format, "float32")) {
            float *t = malloc(n * sizeof(float));
            ret = dirp_measure_ex(h, t, (int32_t)(n * sizeof(float)));
            if (ret == DIRP_SUCCESS) code = ecrire_fichier(sortie, t, n * sizeof(float)) ? 1 : 0;
            free(t);
        } else if (!strcmp(format, "int16")) {
            int16_t *t = malloc(n * sizeof(int16_t));
            ret = dirp_measure(h, t, (int32_t)(n * sizeof(int16_t)));
            if (ret == DIRP_SUCCESS) code = ecrire_fichier(sortie, t, n * sizeof(int16_t)) ? 1 : 0;
            free(t);
        } else {
            fprintf(stderr, "Format inconnu : %s (float32 ou int16)\n", format);
            code = 2;
            goto fin;
        }
        if (ret != DIRP_SUCCESS) {
            fprintf(stderr, "Mesure impossible : %d (%s)\n", ret, message(ret));
            code = 5;
        } else if (verbeux) {
            fprintf(stderr, "%s : %ux%u, %s -> %s\n", source, res.width, res.height, format, sortie);
        }
    } else if (!strcmp(action, "extract")) {
        uint16_t *raw = malloc(n * sizeof(uint16_t));
        ret = dirp_get_original_raw(h, raw, (int32_t)(n * sizeof(uint16_t)));
        if (ret == DIRP_SUCCESS) code = ecrire_fichier(sortie, raw, n * sizeof(uint16_t)) ? 1 : 0;
        else { fprintf(stderr, "Extraction impossible : %d (%s)\n", ret, message(ret)); code = 5; }
        free(raw);
    } else {
        fprintf(stderr, "Action inconnue : %s\n", action);
        code = 2;
    }

fin:
    dirp_destroy(h);
    free(donnees);
    return code;
}
