#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickStyle>
#include <QDebug>

#include "viewmodel/OptionsFileModel.h"
#include "viewmodel/SectionListModel.h"
#include "viewmodel/PropertyTreeModel.h"
#include "core/HashLookup.h"

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);
    app.setApplicationName("ACB Options Editor");
    app.setOrganizationName("ACBSerializer");
    app.setApplicationVersion("1.0.0");

    // Use Fusion style for consistent cross-platform look
    QQuickStyle::setStyle("Fusion");

    // Load hash mappings from default locations
    if (acb::HashLookup::loadDefaults()) {
        qDebug() << "Loaded" << acb::HashLookup::hashCount() << "hash mappings";
    }

    // Register QML types
    qmlRegisterType<acb::OptionsFileModel>("AcbOptionsEditor", 1, 0, "OptionsFileModel");
    qmlRegisterType<acb::SectionListModel>("AcbOptionsEditor", 1, 0, "SectionListModel");
    qmlRegisterType<acb::PropertyTreeModel>("AcbOptionsEditor", 1, 0, "PropertyTreeModel");

    QQmlApplicationEngine engine;

    const QUrl url(QStringLiteral("qrc:/AcbOptionsEditor/qml/main.qml"));
    QObject::connect(&engine, &QQmlApplicationEngine::objectCreated,
                     &app, [url](QObject *obj, const QUrl &objUrl) {
        if (!obj && url == objUrl)
            QCoreApplication::exit(-1);
    }, Qt::QueuedConnection);

    engine.load(url);

    return app.exec();
}
