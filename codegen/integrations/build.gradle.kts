// AWS SDK customizations of smithy-python client codegen, loaded by the harness
// in the parent project through the PythonIntegration service loader.

plugins {
    `java-library`
}

repositories {
    mavenLocal()
    mavenCentral()
}

val codegenVersion: String by rootProject.extra
val smithyVersion: String by rootProject.extra

dependencies {
    implementation("software.amazon.smithy.python.codegen:core:$codegenVersion")
    implementation("software.amazon.smithy:smithy-aws-traits:$smithyVersion")

    testImplementation(platform("org.junit:junit-bom:6.1.3"))
    testImplementation("org.junit.jupiter:junit-jupiter-api")
    testRuntimeOnly("org.junit.jupiter:junit-jupiter-engine")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(17)
    }
}

val repoRoot = rootProject.projectDir.parentFile

tasks.processResources {
    // The repository root's LICENSE and NOTICE are the single source for every client.
    from(repoRoot) {
        include("LICENSE", "NOTICE")
        into("software/amazon/aws/sdk/python/codegen")
    }
}

tasks.test {
    useJUnitPlatform()
    systemProperty("repoRoot", repoRoot.absolutePath)
}
