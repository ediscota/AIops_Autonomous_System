# Stage 1: Build
FROM eclipse-temurin:17-jdk-jammy AS build
WORKDIR /app

COPY .mvn/ .mvn
COPY mvnw pom.xml ./
RUN chmod +x mvnw
RUN ./mvnw dependency:go-offline

# --- PUNTO CRITICO ---
# Copiamo i sorgenti
COPY src ./src

# DEBUG: Stampa tutti i file .java trovati. 
# Se nei log non vedi ApiController, Docker non lo sta copiando!
RUN find src -name "*.java"

# Compila forzando "clean" per rimuovere vecchi target
RUN ./mvnw clean package -DskipTests

# Stage 2: Run
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
COPY --from=build /app/target/*.jar app.jar
ENTRYPOINT ["java", "-jar", "app.jar"]