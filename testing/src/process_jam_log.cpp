//  process jam regression test output into XML  -----------------------------//

//  Copyright Beman Dawes 2002.
//  Copyright Rene Rivera 2015.
//  Distributed under the Boost
//  Software License, Version 1.0. (See accompanying file
//  LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)

//  See http://www.boost.org/tools/regression for documentation.

#include <string>
#include <vector>


extern int process_jam_log( const std::vector<std::string> & args );


//  main  --------------------------------------------------------------------//


int main( int argc, char ** argv )
{
  std::vector<std::string> args;
  while ( argc > 1 )
  {
    args.push_back( argv[1] );
    --argc; ++argv;
  }
  return process_jam_log( args );
}
