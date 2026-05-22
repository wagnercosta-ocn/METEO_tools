#
# Statistiques a partir de sortie de allgfopoint_test.f
#
# -------------------------------------------------------

library(fields)
library(gplots,
        lib.loc="/home/mf/dp/mpma/aoufl/R/x86_64-pc-linux-gnu-library/3.6/")
library(RColorBrewer)
library(sp)
library(mapdata)
library(maps)

# -------------------------------------------------------
# Lecture des données
# -------------------------------------------------------

donn = read.table("testcheck", header = FALSE, dec = ".")

# résolution des données dans le plot (°)
res = 0.7

# largeur des plots
pwidth = 811

# hauteur des plots
pheight = 402

# min/max de la légende du biais
Min_biais = -80
Max_biais = 80

# nb de couleurs pour le biais
nbcol_biais = 30

# min/max de la légende du si
Min_si = 2
Max_si = 22

# nb de couleurs pour le si
nbcol_si = 18

# IMPORTANT :
# noms de colonnes uniques
colnames(donn) = c(
  "lon",
  "lat",
  "bias_mod1",
  "bias_mod2",
  "Vent",
  "model_mod1",
  "model_mod2",
  "obs"
)

# -------------------------------------------------------
# Filtrage des données
# -------------------------------------------------------

# filtrage d'éventuel point non complet
donn = donn[donn$model_mod1 > 0.5, ]
donn = donn[donn$model_mod1 < 12, ]

donn = donn[donn$model_mod2 > 0.5, ]
donn = donn[donn$model_mod2 < 12, ]

donn = donn[donn$obs > 0.5, ]
donn = donn[donn$obs < 12, ]

# -------------------------------------------------------
# Filtrage des données aberrantes
# -------------------------------------------------------

print("% données aberrantes")

hsmin = apply(abs(donn[, c("bias_mod1", "bias_mod2")]), 1, min)

print(sum(hsmin > 3) / length(hsmin))

donn = donn[hsmin <= 3, ]

# -------------------------------------------------------
# Quelques stats
# -------------------------------------------------------

print("Population")
print(length(donn[,1]))

print("Biais des modeles")
print(round(
  sapply(donn[, c("bias_mod1", "bias_mod2")], mean),
  2
))

print("RMSE")
print(round(
  sqrt(sapply(
    donn[, c("bias_mod1", "bias_mod2")]^2,
    mean
  )),
  3
))

print("RMSE(%)")
print(round(
  sqrt(sapply(
    donn[, c("bias_mod1", "bias_mod2")]^2,
    mean
  )) / mean(donn$obs, na.rm = TRUE),
  3
))

print("correlation")
print(round(
  sapply(
    donn[, c("model_mod1", "model_mod2")],
    cor,
    donn$obs
  ),
  3
))

print("Scatter Index")
print(round(
  sapply(
    donn[, c("bias_mod1", "bias_mod2")],
    sd
  ) / mean(donn$obs, na.rm = TRUE),
  3
))

# -------------------------------------------------------
# Tracé des scatterplots
# -------------------------------------------------------

# max de hs pour les axes
maxhs = trunc(max(
  max(donn$model_mod1),
  max(donn$model_mod2),
  max(donn$obs, na.rm = TRUE)
)) + 2

# histogrammes 2D
h1 = hist2d(
  data.frame(donn$obs, donn$model_mod1),
  nbins = 30,
  col = tim.colors(25),
  FUN = function(x) log(length(x)),
  xlim = c(0, maxhs),
  ylim = c(0, maxhs),
  same.scale = TRUE
)

h2 = hist2d(
  data.frame(donn$obs, donn$model_mod2),
  nbins = 30,
  col = tim.colors(25),
  FUN = function(x) log(length(x)),
  xlim = c(0, maxhs),
  ylim = c(0, maxhs),
  same.scale = TRUE
)

maxfreq = round(exp(max(h1$counts, h2$counts, na.rm = TRUE)), 0) + 1

pal = exp(seq(
  from = log(1),
  to = log(maxfreq),
  length.out = 26
))

# -------------------------------------------------------
# Scatter MOD1
# -------------------------------------------------------

png(
  "scatter_mod1.png",
  width = pwidth,
  height = pheight,
  res = 300
)

par(mar = c(9,4,2,1))

hist2d(
  data.frame(donn$obs, donn$model_mod1),
  nbins = 30,
  col = tim.colors(25),
  FUN = function(x) log(length(x)),
  xlim = c(0, maxhs),
  ylim = c(0, maxhs),
  same.scale = TRUE,
  xlab = "Altimeter wave height (m)",
  ylab = "Model1 (m)"
)

abline(a = 0, b = 1, col = "black")

orth = prcomp(~ donn$obs + donn$model_mod1)

slope = orth$rotation[2,1] / orth$rotation[1,1]

interc = orth$center[2] - slope * orth$center[1]

print("Slope")
print(slope)

print("Intercept")
print(interc)

abline(a = interc, b = slope, col = "red")

image.plot(
  h1,
  col = tim.colors(25),
  breaks = log(pal),
  attr = 1,
  legend.only = TRUE,
  zlim = c(0, log(maxfreq)),
  horizontal = TRUE,
  nlevel = 25,
  axis.args = list(
    cex.axis = 1.5,
    at = log(pal[seq(1, length(pal), 5)]),
    labels = round(pal[seq(1, length(pal), 5)])
  ),
  legend.width = 1.5
)

dev.off()

# -------------------------------------------------------
# Scatter MOD2
# -------------------------------------------------------

png(
  "scatter_mod2.png",
  width = pwidth,
  height = pheight,
  res = 300
)

par(mar = c(9,4,2,1))

hist2d(
  data.frame(donn$obs, donn$model_mod2),
  nbins = 30,
  col = tim.colors(25),
  FUN = function(x) log(length(x)),
  xlim = c(0, maxhs),
  ylim = c(0, maxhs),
  same.scale = TRUE,
  xlab = "Altimeter wave height (m)",
  ylab = "Model2 (m)"
)

abline(a = 0, b = 1, col = "black")

orth = prcomp(~ donn$obs + donn$model_mod2)

slope = orth$rotation[2,1] / orth$rotation[1,1]

interc = orth$center[2] - slope * orth$center[1]

print("Slope")
print(slope)

print("Intercept")
print(interc)

abline(a = interc, b = slope, col = "red")

image.plot(
  h2,
  col = tim.colors(25),
  breaks = log(pal),
  attr = 1,
  legend.only = TRUE,
  zlim = c(0, log(maxfreq)),
  horizontal = TRUE,
  nlevel = 25,
  axis.args = list(
    cex.axis = 1.5,
    at = log(pal[seq(1, length(pal), 5)]),
    labels = round(pal[seq(1, length(pal), 5)])
  ),
  legend.width = 1.5
)

dev.off()

# -------------------------------------------------------
# Calcul des stats géographiques
# -------------------------------------------------------

donn$count = 1

# scatter index
moy_mod1 = aggregate(
  donn$bias_mod1,
  by = list(donn$lon, donn$lat),
  sd,
  na.rm = TRUE
)

moy_mod2 = aggregate(
  donn$bias_mod2,
  by = list(donn$lon, donn$lat),
  sd,
  na.rm = TRUE
)

# biais
biais_mod1 = aggregate(
  donn$bias_mod1,
  by = list(donn$lon, donn$lat),
  mean
)

biais_mod2 = aggregate(
  donn$bias_mod2,
  by = list(donn$lon, donn$lat),
  mean
)

moy_obs = aggregate(
  donn$obs,
  by = list(donn$lon, donn$lat),
  mean,
  na.rm = TRUE
)

compt = aggregate(
  donn$count,
  by = list(donn$lon, donn$lat),
  sum
)

# -------------------------------------------------------
# Construction du nouveau dataframe
# -------------------------------------------------------

donn = data.frame(
  lon  = moy_obs[,1],
  lat  = moy_obs[,2],
  b1   = round(biais_mod1[,3], 2),
  b2   = round(biais_mod2[,3], 2),
  si1  = round(moy_mod1[,3] / moy_obs[,3], 2),
  si2  = round(moy_mod2[,3] / moy_obs[,3], 2),
  npts = compt[,3],
  obs  = moy_obs[,3]
)

# -------------------------------------------------------
# IMPORTANT :
# conversion longitude AVANT min/max
# -------------------------------------------------------

donn$lon[donn$lon > 180] =
  donn$lon[donn$lon > 180] - 360

# arrondi pour éviter les problèmes
# de précision numérique
donn$lon = round(donn$lon, 3)
donn$lat = round(donn$lat, 3)

latmin = min(donn$lat, na.rm = TRUE)
latmax = max(donn$lat, na.rm = TRUE)

lonmin = min(donn$lon, na.rm = TRUE)
lonmax = max(donn$lon, na.rm = TRUE)

# -------------------------------------------------------
# IMPORTANT :
# PAS de gridded(donn)=TRUE
# quilt.plot fonctionne avec des points
# irréguliers
# -------------------------------------------------------

coordinates(donn) = c("lon", "lat")

# -------------------------------------------------------
# Tracé des biais
# -------------------------------------------------------

tik = seq(
  Min_biais,
  Max_biais,
  length = nbcol_biais + 1
)

colors = brewer.pal(10, "RdBu")

mypal = colorRampPalette(colors)

# suppression des NA
donn = donn[!is.na(donn$b1), ]
donn = donn[!is.na(donn$b2), ]

# passage en cm
donn$b1 = 100 * donn$b1
donn$b2 = 100 * donn$b2

# -------------------------------------------------------
# Biais MOD1
# -------------------------------------------------------

png(
  "biais_mod1.png",
  width = pwidth,
  height = pheight,
  res = 300
)

par(mar = c(2,2,1,1))

quilt.plot(
  coordinates(donn),
  donn$b1,
  col = rev(mypal(nbcol_biais)),
  breaks = tik,
  zlim = c(Min_biais, Max_biais),
  axes = TRUE,
  legend.lab = "Bias in cm"
)

map('worldHires',
    add = TRUE,
    col = "black",
    fill = FALSE)

dev.off()

# -------------------------------------------------------
# Biais MOD2
# -------------------------------------------------------

png(
  "biais_mod2.png",
  width = pwidth,
  height = pheight,
  res = 300
)

par(mar = c(2,2,1,1))

quilt.plot(
  coordinates(donn),
  donn$b2,
  col = rev(mypal(nbcol_biais)),
  breaks = tik,
  zlim = c(Min_biais, Max_biais),
  axes = TRUE,
  legend.lab = "Bias in cm"
)

map('worldHires',
    add = TRUE,
    col = "black",
    fill = FALSE)

dev.off()

# -------------------------------------------------------
# Tracé des scatter index
# -------------------------------------------------------

tik = seq(
  Min_si,
  Max_si,
  length = nbcol_si + 1
)

# suppression des NA
donn = donn[!is.na(donn$si1), ]
donn = donn[!is.na(donn$si2), ]

# passage en %
donn$si1 = 100 * donn$si1
donn$si2 = 100 * donn$si2

# -------------------------------------------------------
# SI MOD1
# -------------------------------------------------------

png(
  "si_mod1.png",
  width = pwidth,
  height = pheight,
  res = 300
)

par(mar = c(2,2,1,1))

quilt.plot(
  coordinates(donn),
  donn$si1,
  col = tim.colors(nbcol_si),
  breaks = tik,
  zlim = c(Min_si, Max_si),
  axes = TRUE,
  legend.lab = "SI in %"
)

map('worldHires',
    add = TRUE,
    col = "black",
    fill = FALSE)

dev.off()

# -------------------------------------------------------
# SI MOD2
# -------------------------------------------------------

png(
  "si_mod2.png",
  width = pwidth,
  height = pheight,
  res = 300
)

par(mar = c(2,2,1,1))

quilt.plot(
  coordinates(donn),
  donn$si2,
  col = tim.colors(nbcol_si),
  breaks = tik,
  zlim = c(Min_si, Max_si),
  axes = TRUE,
  legend.lab = "SI in %"
)

map('worldHires',
    add = TRUE,
    col = "black",
    fill = FALSE)

dev.off()
