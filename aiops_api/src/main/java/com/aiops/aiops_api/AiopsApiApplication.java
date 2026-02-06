package com.aiops.aiops_api;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

@SpringBootApplication
@ComponentScan(basePackages = "com.aiops.aiops_api")
public class AiopsApiApplication {

	public static void main(String[] args) {
		SpringApplication.run(AiopsApiApplication.class, args);
	}

}
