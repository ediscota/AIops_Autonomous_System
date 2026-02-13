# Stage 1: Build
FROM eclipse-temurin:17-jdk-jammy AS build
WORKDIR /app

COPY .mvn/ .mvn
COPY mvnw pom.xml ./
RUN chmod +x mvnw
RUN ./mvnw dependency:go-offline

# CRITICAL POINT
# Copying the source files
COPY src ./src

# DEBUG: Prints al the .java files who have been found. 
# If in the log you can't see ApiController, then in means Docker is not copying it!
RUN find src -name "*.java"

# Compile using "clean" to remove the old target folder
RUN ./mvnw clean package -DskipTests

# Stage 2: Run
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
COPY --from=build /app/target/*.jar app.jar
ENTRYPOINT ["java", "-jar", "app.jar"]