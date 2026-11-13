/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
package software.amazon.aws.sdk.python.codegen;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.List;
import org.junit.jupiter.api.Test;
import software.amazon.smithy.aws.traits.ServiceTrait;
import software.amazon.smithy.build.MockManifest;
import software.amazon.smithy.model.Model;
import software.amazon.smithy.model.shapes.ServiceShape;
import software.amazon.smithy.python.codegen.GenerationContext;
import software.amazon.smithy.python.codegen.PythonSettings;
import software.amazon.smithy.python.codegen.PythonSymbolProvider;
import software.amazon.smithy.python.codegen.writer.PythonDelegator;

public class S3HeadNotFoundIntegrationTest {

    @Test
    public void appliesOnlyToS3() {
        assertEquals(List.of(true, false), List.of(matches("S3"), matches("S3 Control")));
    }

    private static boolean matches(String sdkId) {
        var service = ServiceShape.builder()
                .id("com.amazonaws.example#Example")
                .version("2006-03-01")
                .addTrait(ServiceTrait.builder()
                        .sdkId(sdkId)
                        .arnNamespace("example")
                        .cloudFormationName("Example")
                        .cloudTrailEventSource("example.amazonaws.com")
                        .endpointPrefix("example")
                        .build())
                .build();
        var model = Model.builder().addShape(service).build();
        var settings = PythonSettings.builder()
                .service(service.getId())
                .moduleName("aws_sdk_example")
                .moduleVersion("0.0.1")
                .build();
        var manifest = new MockManifest();
        var context = GenerationContext.builder()
                .model(model)
                .settings(settings)
                .fileManifest(manifest)
                .writerDelegator(new PythonDelegator(manifest, new PythonSymbolProvider(model, settings), settings))
                .build();
        var plugins = new S3HeadNotFoundIntegration().getClientPlugins(context);
        return plugins.get(0).matchesService(model, service);
    }
}
