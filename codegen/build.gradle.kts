// Code generation harness. Runs the smithy-python `python-client-codegen`
// build plugin against one AWS service model to (re)generate a single client.
// The codegen jars are resolved from the local Maven cache; publish them from
// the colocated smithy-python checkout with `make publish-codegen` first.

plugins {
    java
    id("software.amazon.smithy.gradle.smithy-base") version "1.5.0"
}

repositories {
    mavenLocal()
    mavenCentral()
}

val smithyVersion = "1.73.0"
val codegenVersion = "0.5.1"

dependencies {
    // The build plugin (`python-client-codegen`) and AWS customizations must be
    // on the smithy build classpath for the projection to resolve them.
    smithyBuild("software.amazon.smithy.python.codegen:core:$codegenVersion")
    smithyBuild("software.amazon.smithy.python.codegen.aws:core:$codegenVersion")

    // AWS + Smithy trait packages used across the service models
    // (aws.api/auth/protocols, aws.iam, aws.cloudformation, endpoints/rules,
    // waiters, smoke tests).
    smithyBuild("software.amazon.smithy:smithy-aws-traits:$smithyVersion")
    smithyBuild("software.amazon.smithy:smithy-aws-iam-traits:$smithyVersion")
    smithyBuild("software.amazon.smithy:smithy-aws-cloudformation-traits:$smithyVersion")
    smithyBuild("software.amazon.smithy:smithy-aws-endpoints:$smithyVersion")
    smithyBuild("software.amazon.smithy:smithy-rules-engine:$smithyVersion")
    smithyBuild("software.amazon.smithy:smithy-protocol-traits:$smithyVersion")
    smithyBuild("software.amazon.smithy:smithy-waiters:$smithyVersion")
    smithyBuild("software.amazon.smithy:smithy-smoke-test-traits:$smithyVersion")
    // Defines aws.test#AwsVendorParams, referenced by service smokeTests traits.
    smithyBuild("software.amazon.smithy:smithy-aws-smoke-test-model:$smithyVersion")
}
