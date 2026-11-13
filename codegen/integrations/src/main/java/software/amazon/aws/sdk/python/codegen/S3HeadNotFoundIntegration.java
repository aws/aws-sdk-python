/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
package software.amazon.aws.sdk.python.codegen;

import java.util.List;
import software.amazon.smithy.aws.traits.ServiceTrait;
import software.amazon.smithy.codegen.core.Symbol;
import software.amazon.smithy.codegen.core.SymbolReference;
import software.amazon.smithy.model.shapes.ServiceShape;
import software.amazon.smithy.model.shapes.ShapeId;
import software.amazon.smithy.python.codegen.CodegenUtils;
import software.amazon.smithy.python.codegen.GenerationContext;
import software.amazon.smithy.python.codegen.PythonDependency;
import software.amazon.smithy.python.codegen.SmithyPythonDependency;
import software.amazon.smithy.python.codegen.SyncVariant;
import software.amazon.smithy.python.codegen.integrations.PythonIntegration;
import software.amazon.smithy.python.codegen.integrations.RuntimeClientPlugin;

/**
 * Raises S3's modeled {@code NotFound} for a 404 response to a HEAD request, on the operations that model it.
 */
public final class S3HeadNotFoundIntegration implements PythonIntegration {

    private static final String FILE = "head_errors";
    private static final ShapeId NOT_FOUND = ShapeId.from("com.amazonaws.s3#NotFound");

    // S3 can't send an error code in a HEAD response, which has no body.
    private static final String INTERCEPTOR_MODULE = """
            class HeadNotFoundInterceptor($1T[Any, Any, $2T, $3T]):
                \"\"\"Raises NotFound for a 404 response to a HEAD request.\"\"\"

                def modify_before_deserialization(
                    self, context: $4T[Any, $2T, $3T]
                ) -> $3T:
                    response = context.transport_response
                    if context.transport_request.method == "HEAD" and response.status == 404:
                        raise $5T(response.reason or "Not Found")
                    return response
            """;

    private static final String PLUGIN_MODULE = """
            def head_not_found_plugin(config: $1T) -> None:
                config.interceptors.append($2T())
            """;

    private static final Symbol INTERCEPTOR_BASE = runtimeSymbol(
            "smithy_core.interceptors", "Interceptor", SmithyPythonDependency.SMITHY_CORE);
    private static final Symbol RESPONSE_CONTEXT = runtimeSymbol(
            "smithy_core.interceptors", "ResponseContext", SmithyPythonDependency.SMITHY_CORE);
    private static final Symbol REQUEST_INTERFACE = runtimeSymbol(
            "smithy_http.interfaces", "HTTPRequest", SmithyPythonDependency.SMITHY_HTTP);
    private static final Symbol RESPONSE_INTERFACE = runtimeSymbol(
            "smithy_http.interfaces", "HTTPResponse", SmithyPythonDependency.SMITHY_HTTP);

    @Override
    public List<RuntimeClientPlugin> getClientPlugins(GenerationContext context) {
        var moduleName = context.settings().moduleName();
        var interceptor = Symbol.builder()
                .name("HeadNotFoundInterceptor")
                .namespace(moduleName + "._private." + FILE, ".")
                .definitionFile("./src/" + moduleName + "/_private/" + FILE + ".py")
                .build();
        var plugin = SymbolReference.builder()
                .symbol(CodegenUtils.aioSymbol(context.settings(), FILE, "head_not_found_plugin"))
                .build();

        // The generator writes a plugin's files only when its service predicate matches, which an
        // operation-scoped plugin never does, so the files come from a separate service-level plugin.
        var files = RuntimeClientPlugin.builder()
                .servicePredicate((model, service) -> isS3(service))
                .writeAdditionalFiles(c -> {
                    c.writerDelegator()
                            .useFileWriter(interceptor.getDefinitionFile(), interceptor.getNamespace(), writer -> {
                                var notFound = c.symbolProvider().toSymbol(c.model().expectShape(NOT_FOUND));
                                writer.addStdlibImport("typing", "Any");
                                writer.write(INTERCEPTOR_MODULE,
                                        INTERCEPTOR_BASE,
                                        REQUEST_INTERFACE,
                                        RESPONSE_INTERFACE,
                                        RESPONSE_CONTEXT,
                                        notFound);
                            });
                    var pluginFile = plugin.getSymbol().getDefinitionFile();
                    var asyncConfig = CodegenUtils.getAsyncConfigSymbol(c.settings(), c.model());
                    c.writerDelegator()
                            .useFileWriter(pluginFile, plugin.getSymbol().getNamespace(), writer -> {
                                writer.write(PLUGIN_MODULE, asyncConfig, interceptor);
                            });
                    return List.of(
                            interceptor.getDefinitionFile(),
                            pluginFile,
                            SyncVariant.writeSyncTwin(c, plugin.getSymbol(), PLUGIN_MODULE, asyncConfig, interceptor));
                })
                .build();

        var operations = RuntimeClientPlugin.builder()
                .operationPredicate((model, service, operation) -> isS3(service)
                        && operation.getErrors().contains(NOT_FOUND))
                .pythonPlugin(plugin)
                .build();

        return List.of(files, operations);
    }

    private static boolean isS3(ServiceShape service) {
        return service.getTrait(ServiceTrait.class)
                .map(trait -> trait.getSdkId().equals("S3"))
                .orElse(false);
    }

    private static Symbol runtimeSymbol(String namespace, String name, PythonDependency dependency) {
        return Symbol.builder()
                .namespace(namespace, ".")
                .name(name)
                .addDependency(dependency)
                .build();
    }
}
