/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
package software.amazon.aws.sdk.python.codegen;

import java.util.List;
import software.amazon.smithy.aws.traits.ServiceTrait;
import software.amazon.smithy.model.traits.TitleTrait;
import software.amazon.smithy.python.codegen.GenerationContext;
import software.amazon.smithy.python.codegen.integrations.PythonIntegration;
import software.amazon.smithy.python.codegen.sections.ReadmeSection;
import software.amazon.smithy.python.codegen.writer.PythonWriter;
import software.amazon.smithy.utils.CodeInterceptor;
import software.amazon.smithy.utils.CodeSection;

/**
 * Writes the AWS SDK README, LICENSE, and NOTICE into each generated client package.
 */
public final class AwsSdkPackageFilesIntegration implements PythonIntegration {

    // Copied from the repository root at build time; see build.gradle.kts.
    private static final List<String> LEGAL_FILES = List.of("LICENSE", "NOTICE");

    @Override
    public List<? extends CodeInterceptor<? extends CodeSection, PythonWriter>> interceptors(
            GenerationContext context
    ) {
        return List.of(new ReadmeInterceptor(context));
    }

    @Override
    public void customize(GenerationContext context) {
        for (var name : LEGAL_FILES) {
            context.fileManifest().writeFile(name, AwsSdkPackageFilesIntegration.class, name);
        }
    }

    private static final class ReadmeInterceptor implements CodeInterceptor<ReadmeSection, PythonWriter> {

        private final GenerationContext context;

        ReadmeInterceptor(GenerationContext context) {
            this.context = context;
        }

        @Override
        public Class<ReadmeSection> sectionType() {
            return ReadmeSection.class;
        }

        @Override
        public void write(PythonWriter writer, String previousText, ReadmeSection section) {
            var service = context.settings().service(context.model());
            var title = service.expectTrait(TitleTrait.class).getValue();
            var sdkId = service.expectTrait(ServiceTrait.class).getSdkId();
            var packageName = context.settings().moduleName().replace('_', '-');
            var docsSlug = packageName.substring("aws-sdk-".length());
            writer.write("""
                    # $1L Client

                    The `$2L` package provides a client for making
                    requests to $1L.

                    > **Note:** This SDK is experimental and in early development. Breaking changes
                    > may occur prior to the release of version 1.0.0.

                    ## Installation

                    ```bash
                    python -m pip install $2L
                    ```

                    ## Documentation

                    - [API Reference](https://docs.aws.amazon.com/sdk-for-python/v4/reference/clients/$3L/) -
                      the $4L client, available operations, and types.
                    - [Developer Guide](https://docs.aws.amazon.com/sdk-for-python/v4/guide/) -
                      configuration, authentication, and usage of the AWS SDK for Python v4.""",
                    title,
                    packageName,
                    docsSlug,
                    sdkId);
        }
    }
}
