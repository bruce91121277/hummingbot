from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy
names=['hummingbot.core.event.event_listener','hummingbot.core.pubsub','hummingbot.core.data_type.order_book_query_result','hummingbot.core.data_type.order_book']
extensions=[]
for name in names:
    sources=[name.replace('.','/')+'.pyx']
    if name.endswith('.pubsub'): sources.append('hummingbot/core/cpp/PyRef.cpp')
    if name.endswith('.order_book'): sources.append('hummingbot/core/cpp/OrderBookEntry.cpp')
    extensions.append(Extension(name,sources,language='c++',include_dirs=[numpy.get_include(),'.']))
setup(name='hb-research-core',ext_modules=cythonize(extensions,language_level=3))