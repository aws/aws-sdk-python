/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
package software.amazon.aws.sdk.python.codegen;

import java.util.List;
import software.amazon.smithy.aws.traits.ServiceTrait;
import software.amazon.smithy.codegen.core.Symbol;
import software.amazon.smithy.codegen.core.SymbolReference;
import software.amazon.smithy.python.codegen.CodegenUtils;
import software.amazon.smithy.python.codegen.GenerationContext;
import software.amazon.smithy.python.codegen.PythonDependency;
import software.amazon.smithy.python.codegen.SmithyPythonDependency;
import software.amazon.smithy.python.codegen.SyncVariant;
import software.amazon.smithy.python.codegen.integrations.PythonIntegration;
import software.amazon.smithy.python.codegen.integrations.RuntimeClientPlugin;

/**
 * Raises S3's modeled {@code NotFound} for a 404 response to a HEAD request.
 */
public final class S3HeadNotFoundIntegration implements PythonIntegration {

    private static final String FILE = "head_errors";

    // S3 can't send an error code in a HEAD response, which has no body.
    private static final String INTERCEPTOR_MODULE = """
            _NOT_FOUND_BODY = b"<Error><Code>NotFound</Code></Error>"


            class HeadNotFoundInterceptor($1T[Any, Any, $2T, $3T]):
                \"\"\"Gives a 404 response to a HEAD request the NotFound error code.\"\"\"

                def modify_before_deserialization(
                    self, context: $4T[Any, $2T, $3T]
                ) -> $3T:
                    response = context.transport_response
                    if context.transport_request.method != "HEAD" or response.status != 404:
                        return response
                    return $5T(
                        status=response.status,
                        fields=response.fields,
                        reason=response.reason,
                        body=_NOT_FOUND_BODY,
                    )
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
    private static final Symbol RESPONSE = runtimeSymbol(
            "smithy_http", "HTTPResponse", SmithyPythonDependency.SMITHY_HTTP);

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

        return List.of(RuntimeClientPlugin.builder()
                .servicePredicate((model, service) -> service.getTrait(ServiceTrait.class)
                        .map(trait -> trait.getSdkId().equals("S3"))
                        .orElse(false))
                .pythonPlugin(plugin)
                .writeAdditionalFiles(c -> {
                    c.writerDelegator()
                            .useFileWriter(interceptor.getDefinitionFile(), interceptor.getNamespace(), writer -> {
                                writer.addStdlibImport("typing", "Any");
                                writer.write(INTERCEPTOR_MODULE,
                                        INTERCEPTOR_BASE,
                                        REQUEST_INTERFACE,
                                        RESPONSE_INTERFACE,
                                        RESPONSE_CONTEXT,
                                        RESPONSE);
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
                .build());
    }

    private static Symbol runtimeSymbol(String namespace, String name, PythonDependency dependency) {
        return Symbol.builder()
                .namespace(namespace, ".")
                .name(name)
                .addDependency(dependency)
                .build();
    }
}
